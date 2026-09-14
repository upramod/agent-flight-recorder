import { ActionEvent } from "./types.js";

export interface AgentProposal {
  action: ActionEvent;
  explanation?: string;
}

export interface AzureAgentConfig {
  endpoint: string;
  deployment: string;
  apiKey: string;
  apiVersion: string;
}

export function azureConfigFromEnvironment(): AzureAgentConfig {
  const values = {
    endpoint: process.env.AZURE_OPENAI_ENDPOINT,
    deployment: process.env.AZURE_OPENAI_DEPLOYMENT,
    apiKey: process.env.AZURE_OPENAI_API_KEY,
    apiVersion: process.env.AZURE_OPENAI_API_VERSION ?? "2024-10-21"
  };

  if (!values.endpoint || !values.deployment || !values.apiKey) {
    throw new Error(
      "Azure OpenAI configuration is incomplete. Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, and AZURE_OPENAI_API_KEY."
    );
  }

  return values as AzureAgentConfig;
}

export async function requestAgentProposal(
  config: AzureAgentConfig,
  instruction: string
): Promise<AgentProposal> {
  const endpoint = config.endpoint.replace(/\/$/, "");
  const url =
    endpoint +
    "/openai/deployments/" +
    encodeURIComponent(config.deployment) +
    "/chat/completions?api-version=" +
    encodeURIComponent(config.apiVersion);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "api-key": config.apiKey
    },
    body: JSON.stringify({
      temperature: 0,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content:
            "Return only a JSON object with an action proposal. Include id, sessionId, timestamp, tool, operation, resourceType, sensitivity, destinationTrust, privilegeLevel, inputProvenance, and optional metadata."
        },
        { role: "user", content: instruction }
      ]
    })
  });

  if (!response.ok) {
    throw new Error("Azure OpenAI request failed with HTTP " + response.status);
  }

  const payload = await response.json() as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const content = payload.choices?.[0]?.message?.content;

  if (!content) {
    throw new Error("Azure OpenAI returned no action proposal");
  }

  return JSON.parse(content) as AgentProposal;
}
