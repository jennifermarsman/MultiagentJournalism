# Multiagent Journalism
A group of agents collaborate to help a human journalist craft a compelling article

## Scenario
This repo contains an enterprise journalism scenario implemented using multiple agents collaborating with the **Microsoft Agent Framework**.  Run **journalism.py** for a group of agents to conduct online research to craft a news article.

## Background
This was based off early work done at [MultiagentResearch](https://github.com/jennifermarsman/MultiagentResearch) to support the [Lenfest Institute](https://www.lenfestinstitute.org/institute-news/lenfest-institute-openai-microsoft-ai-collaborative-fellowship/), but rewritten to use the Microsoft Agent Framework instead of AutoGen.  This was presented as a demo for Ignite 2025 that shows the Microsoft Agent Framework with various models and the web_search_preview tool.  The session link is https://ignite.microsoft.com/en-US/sessions/BRK203.  

## Setup
You will first need to create an [Azure OpenAI resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI).  Then deploy two models, one non-reasoning and one reasoning model: `gpt-4o` and `gpt-5.1`.  To experiment with reasoning and non-reasoning models, you may choose different options, but the code assumes these two as default model deployments.  

Copy the .env.template file into a new file called .env, and update the .env file with the endpoint (and the deployment names if you change from the defaults).  You will also need to supply either an API key or use Microsoft Entra ID (formerly called Azure Active Directory) authentication. We strongly recommend Microsoft Entra ID authentication for greater security. To set it up, see https://learn.microsoft.com/azure/ai-services/openai/how-to/managed-identity. Don't forget that you may need to run "az login" to refresh your credentials.

Finally, use the following commands in a python environment (such as an Anaconda prompt window) to set up your environment. This creates and activates an environment and installs the required packages. For subsequent runs after the initial install, you will only need to activate the environment and then run the python script.

### First run
```
conda create --name journalism -y
conda activate journalism

pip install -r requirements.txt
python journalism.py
```

### Subsequent runs
```
conda activate journalism
python journalism.py
```

### Authentication
The code supports two authentication methods:
1. **Azure CLI (Recommended)**: Run `az login` before executing the script
2. **API Key**: Set `AZURE_OPENAI_API_KEY` in your .env file
