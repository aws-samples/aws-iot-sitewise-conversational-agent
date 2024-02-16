import json
import boto3
import logging
import datetime
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sw_client = boto3.client("iotsitewise", region_name=os.environ.get('AWS_REGION'))

def _get_named_parameter(event, name):
    """
    get the parameter 'name' from the lambda event object
    Args:
        event: lambda event
        name: name of the parameter to return
    Returns:
        parameter value
    """
    return next(item for item in event['parameters'] if item['name'] == name)['value']


def _get_named_property(event, name):
    """
    get the named property 'name' from the lambda event object
    Args:        
        event: lambda event
        name: name of the named property to return
    Returns:
        named property value
    """
    return next(item for item in event['requestBody']['content']['application/json']['properties'] if item['name'] == name)['value']

def _execute_sitewise_query(sw_client, query_statement, max_results=20):
    """
    Run a query using the IoT SiteWise SQL engine
    Args:
        sw_client: IoT SiteWise client
        query_statement: SQL query
        max_results: max number of query results to return
    Returns:
        dict with results from query
    """
    try:
        result = sw_client.execute_query(queryStatement=query_statement, maxResults=max_results)
        logger.info('Query executed successfully')
        columns = [col['name'] for col in result['columns']]
        data = {}
        for index, col in enumerate(columns):
            col_data = []
            for row in result['rows']:
                cell = row['data'][index]
                if 'scalarValue' in cell:
                    col_data.append(cell['scalarValue'])
                elif 'stringValue' in cell:
                    col_data.append(cell['stringValue'])
                else:
                    col_data.append(None)
            data[col] = col_data
        return data
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return None


def _get_asset_name(sw_client, asset_id):
    """
    get the asset name using the DescribeAsset API
    Args:
        sw_client: IoT SiteWise client
        asset_id: asset id
    Returns:
        asset name
    """
    try:
        asset_information = sw_client.describe_asset(assetId=asset_id)
        asset_name = asset_information['assetName']
        return model_name
    except Exception as e:
        logger.error(f"Error searching for {asset_id}: {e}")
        raise

def _get_asset_id(sw_client, asset_name, maxResults=1):
    """
    Retrieve an asset id by name.
    Args:
        sw_client: IoT SiteWise client
        asset_name: asset name
        maxResults: max number of query results to return
    Returns:
        asset id
    Raises:
        ValueError: If the asset name does not exist or no asset id could be found for the given asset name.
    """
    query_statement = f"SELECT asset_id, asset_name FROM asset WHERE asset_name = '{asset_name}'"
    data = _execute_sitewise_query(sw_client, query_statement, maxResults)
    if data and 'asset_id' in data and data['asset_id']:  # Check if 'asset_id' exists and is not empty
        return data['asset_id'][0]
    else:
        logger.error(f"Asset '{asset_name}' not found.")
        raise ValueError(f"Asset '{asset_name}' not found.")


def _get_model_name(sw_client, model_id):
    """
    get the asset model name using the DescribeAssetModel API
    Args:
        sw_client: IoT SiteWise client
        model_id: model id
    Returns:
        asset model name
    """
    try:
        asset_model_information = sw_client.describe_asset_model(assetModelId=model_id)
        model_name = asset_model_information['assetModelName']
        return model_name
    except Exception as e:
        logger.error(f"Error searching for {model_id}: {e}")
        raise

def _get_property_id(sw_client, asset_id, property_name, maxResults=20):
    """
    get the property id for <property_name> in <asset_id>
    Args:
        sw_client: IoT SiteWise client
        asset_id: asset id
        property name: property name
        maxResults: max number of query results to return
    Returns:
        property id
    """
    query_statement = f"SELECT asset_id, property_id, property_name FROM asset_property WHERE asset_id ='{asset_id}' AND property_name = '{property_name}'"
    data = _execute_sitewise_query(sw_client, query_statement, maxResults)
    if data and 'property_id' in data:
        return data['property_id'][0]
    else:
        raise ValueError(f"Property {property_name} for asset {asset_id} not found")

def _get_property_uom(sw_client, asset_id, property_id):
    """
    Get units of measurement for property using the DescribeAssetProperty API
    Args:
        sw_client: IoT SiteWise client
        asset_id: asset id
        property_id: property id
    Returns:
        tuple with property name and unit (or 'N/A' if not defined)
    """
    try:
        asset_property_information = sw_client.describe_asset_property(assetId=asset_id, propertyId=property_id)
        property_name = asset_property_information['assetProperty']['name']
        property_unit = asset_property_information['assetProperty'].get('unit', '') #handle case where unit is not defined
        return property_name, property_unit
    except Exception as e:
        logger.error(f"Error searching for property {property_id}: {e}")
        raise


def _get_latest_value(sw_client, asset_id, property_id, hoursdelta=-5, maxResults=1):
    """
    Execute a SQL query to get the latest value of <property_id> in <asset_id>
    Args:
        sw_client: IoT SiteWise client
        asset_id: asset id
        property_id: property id
        hoursdelta: difference in hours with respect to UTC time
        maxResults: max number of query results to return
    Returns:
        UNIX timestamp, latest value, unit
    """
    query_statement = f"SELECT asset_id, property_id, event_timestamp, double_value, string_value FROM latest_value_time_series WHERE asset_id = '{asset_id}' AND property_id = '{property_id}'"
    _, unit = _get_property_uom(sw_client, asset_id, property_id)
    data = _execute_sitewise_query(sw_client, query_statement, maxResults)
    if data and 'event_timestamp' in data:
        timestamp = int(int(data['event_timestamp'][0])*1.0e-9)  # convert ns to s
        logger.info(f"Timestamp: {timestamp}")
        datetime_obj = datetime.datetime.utcfromtimestamp(timestamp)
        eastern_tz = datetime.timezone(datetime.timedelta(hours=hoursdelta))  # Adjust for timezone, if necessary
        dt_us_eastern = datetime_obj.astimezone(eastern_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle both numeric and string values
        if 'double_value' in data and data['double_value'][0] is not None:
            measurement = round(float(data['double_value'][0]), 2)
        elif 'string_value' in data and data['string_value'][0] is not None:
            measurement = data['string_value'][0]
        else:
            measurement = 'N/A'  # Or some placeholder if no value is available
        
        logger.info(f"Latest measurement was {measurement} {unit} at {dt_us_eastern}")
        return dt_us_eastern, measurement, unit
    else:
        raise ValueError(f"Latest value for property {property_id} on asset {asset_id} not found")


def get_latest_value(sw_client, asset_name, property_name, maxResults=1):
    """
    get the latest value for the property of an asset
    Args:
        sw_client: IoT SiteWise client
        asset_name: asset name
        property_name: property name
    Returns:
        asset id, property id, latest value
    Raises:
        ValueError: If asset or property does not exist.
    """
    try:
        asset_id = _get_asset_id(sw_client, asset_name)
    except ValueError as e:
        logger.error(f"Asset '{asset_name}' not found: {e}")
        return {'error': f"Asset '{asset_name}' not found."}

    try:
        property_id = _get_property_id(sw_client, asset_id, property_name)
    except ValueError as e:
        logger.error(f"Property '{property_name}' not found for asset '{asset_name}': {e}")
        return {'error': f"Property '{property_name}' not found for asset '{asset_name}'."}

    try:
        event_timestamp, latest_value, unit = _get_latest_value(sw_client, asset_id, property_id)
        val_dict = {
            "assetId": asset_id,
            "propertyId": property_id,
            "eventTimestamp": event_timestamp,
            "latestValue": latest_value,
            "units": unit
        }
        return val_dict
    except ValueError as e:
        logger.error(f"Error retrieving latest value for property '{property_name}' on asset '{asset_name}': {e}")
        return {'error': f"Error retrieving latest value for property '{property_name}' on asset '{asset_name}'."}


def list_asset_models(sw_client):
    """
    List all asset models in the AWS SiteWise account.
    Args:
        sw_client: IoT SiteWise client
    Returns:
        List of asset model summaries
    """
    try:
        paginator = sw_client.get_paginator('list_asset_models')
        model_summaries = []
        for page in paginator.paginate():
            model_summaries.extend(page['assetModelSummaries'])
        logger.info('Asset models retrieved successfully')
        return model_summaries
    except Exception as e:
        logger.error(f"Error listing asset models: {e}")
        raise

def list_assets_for_model(sw_client, model_id):
    """
    List all assets for a given asset model ID.
    Args:
        sw_client: IoT SiteWise client
        model_id: Asset model ID
    Returns:
        List of asset summaries
    """
    try:
        paginator = sw_client.get_paginator('list_assets')
        asset_summaries = []
        for page in paginator.paginate(assetModelId=model_id):
            asset_summaries.extend(page['assetSummaries'])
        return asset_summaries
    except Exception as e:
        logger.error(f"Error listing assets for model {model_id}: {e}")
        raise

def list_all_assets(sw_client):
    """
    List all assets across all asset models.
    Args:
        sw_client: IoT SiteWise client
    Returns:
        list of dict containing model id, model name, asset id, asset name
    """
    try:
        assets_by_model = []
        model_summaries = list_asset_models(sw_client)
        for model in model_summaries:
            model_id = model['id']
            model_name = _get_model_name(sw_client, model_id)
            logger.info(f"Model name: '{model_name}'")
            assets = list_assets_for_model(sw_client, model_id)
            assets_by_model.extend([{'modelId': model_id, 'modelName': model_name, 'assetId': asset['id'], 'assetName': asset['name']} for asset in assets])
        logger.info('All assets retrieved successfully')
        return assets_by_model
    except Exception as e:
        logger.error(f"Error listing all assets: {e}")
        raise

def list_all_assets(sw_client):
    """
    List all assets across all asset models.
    Args:
        sw_client: IoT SiteWise client
    Returns:
        list of dict containing model id, model name, asset id, asset name
    """
    try:
        assets_by_model = []
        model_summaries = list_asset_models(sw_client)
        for model in model_summaries:
            model_id = model['id']
            model_name = _get_model_name(sw_client, model_id)
            logger.info(f"Model name: '{model_name}'")
            assets = list_assets_for_model(sw_client, model_id)
            assets_by_model.extend([{'modelId': model_id, 'modelName': model_name, 'assetId': asset['id'], 'assetName': asset['name']} for asset in assets])
        logger.info('All assets retrieved successfully')
        return assets_by_model
    except Exception as e:
        logger.error(f"Error listing all assets: {e}")
        raise

def list_properties_for_asset(sw_client, asset_name):
    """
    List all properties for a given asset name.
    Args:
        sw_client: IoT SiteWise client
        asset_name: Name of the asset
    Returns:
        List of property details (name and ID)
    """
    asset_id = _get_asset_id(sw_client, asset_name)
    try:
        asset_details = sw_client.describe_asset(assetId=asset_id)
        properties_info = asset_details['assetProperties']
        properties_list = [{'name': prop['name'], 'id': prop['id']} for prop in properties_info]
        return properties_list
    except Exception as e:
        logger.error(f"Error listing properties for asset {asset_name}: {e}")
        raise

def lambda_handler(event, context):
    responses = []
    try:
        api_path = event['apiPath']
        logger.info(f'API Path: {api_path}')
        
        # Initialize the response body to an empty string
        body = ""
        
        if api_path == "/measurements/{AssetName}/{PropertyName}":
            asset_name = _get_named_parameter(event, "AssetName")
            property_name = _get_named_parameter(event, "PropertyName")
            body = get_latest_value(sw_client, asset_name, property_name)
        
        elif api_path == "/assets/all":
            body = list_all_assets(sw_client)
        
        elif api_path == "/assets/{AssetName}/properties":
            asset_name = _get_named_parameter(event, "AssetName")
            body = list_properties_for_asset(sw_client, asset_name)
        
        else:
            body = {f"{api_path} is not a valid API path, try another one."}
        
        response_body = {
            'application/json': {
                'body': json.dumps(body)
            }
        }
        
        action_response = {
            'actionGroup': event.get('actionGroup', 'defaultGroup'),
            'apiPath': api_path,
            'httpMethod': event.get('httpMethod', 'GET'),
            'httpStatusCode': 200,
            'responseBody': response_body
        }
        
        responses.append(action_response)
        
        api_response = {
            'messageVersion': '1.0',
            'response': action_response
        }
        
        return api_response

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'An error occurred processing your request.'})
        }
