# Chatbot

This folder contains a chatbot application that interacts with the Agent built in root directory. This chatbot is built using Streamlit and Python.

![image](https://github.com/aws-samples/aws-iot-sitewise-conversational-agent/assets/36416466/f0e0a4fe-4f37-4cf1-9a89-634a1f84635e)


## Prerequisites

Before running the chatbot, ensure that you have the following:

- Python 3.x installed
- AWS account with access to Amazon Bedrock
- Bedrock agent created and the alias ID and agent ID

## Setup

1. (optional) Create a virtual environment:

```bash
python3 -m venv .venv
```

2. (optional) Activate the virtual environment:

```bash
source .venv/bin/activate
```

3. Install the required dependencies:

```bash
pip install -r chatbot/requirements.txt
```

## Environment Variables

To run the application, you need to create a `.env` file to store the necessary environment variables. Follow these steps to set up the `.env` file:

1. Create a new file named `.env` in the directory from where you will be running the chatbot, typically the root directory.

2. Open the `.env` file in a text editor and add the following variables:

   ```text
   AGENT_ALIAS_ID=your_agent_alias_id
   AGENT_ID=your_agent_id
   ```

   Replace `your_agent_alias_id` and `your_agent_id` with your actual Bedrock agent alias ID and agent ID, respectively.

3. (Optional) If you want to specify the AWS region and profile explicitly, add the following variables to the `.env` file:

   ```text
   AWS_REGION=your_aws_region
   AWS_PROFILE=your_aws_profile
   ```

   Replace `your_aws_region` with the AWS region where your Bedrock agent is located (e.g., "us-east-1") and `your_aws_profile` with the name of the AWS profile you want to use for authentication.

4. Save the `.env` file.

Note: If you are running the application on AWS services like EC2, Cloud9, or SageMaker and have attached an appropriate IAM role to your instance or environment, you can omit the `AWS_REGION` and `AWS_PROFILE` variables from the `.env` file. The application will use the default credentials and region associated with the IAM role.

Make sure to keep the `.env` file secure and do not commit it to version control systems like Git. Add `.env` to your `.gitignore` file to prevent accidental commits.

The application will automatically load the environment variables from the `.env` file when it starts.

## Running the Chatbot

To run the chatbot, execute the following command:

```bash
streamlit run chatbot/chat.py
```

This will start the Streamlit application, and you can access the chatbot by opening the provided URL in your web browser.

### Usage

Once the chatbot is running, you can interact with it by entering your messages in the input field. The chatbot will process your messages and provide responses based on the configured Bedrock agent.

You can also select sample questions from the sidebar to quickly populate the input field with predefined questions.

To reset the chat history and start a new conversation, click the "Reset Chat" button in the sidebar.
