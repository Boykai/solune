@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Principal ID of the managed identity — granted Cognitive Services OpenAI User role.')
param identityPrincipalId string

@description('Name for the Azure OpenAI model deployment.')
param openAiModelName string = 'gpt-4o'

@description('Azure OpenAI deployment capacity in thousands of tokens per minute.')
param deployCapacity int = 10

@description('Azure OpenAI account (S0 SKU) for AI content generation.')
resource openAiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'oai-${environmentName}'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'oai-${environmentName}'
    publicNetworkAccess: 'Enabled'
  }
}

@description('GPT-4o model deployment within the Azure OpenAI account.')
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAiAccount
  name: openAiModelName
  sku: {
    name: 'Standard'
    capacity: deployCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
  }
}

@description('Cognitive Services OpenAI User role definition — allows calling AI models.')
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

@description('Assigns Cognitive Services OpenAI User role to the managed identity.')
resource openAiUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiAccount.id, identityPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAiAccount
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalType: 'ServicePrincipal'
  }
}

@description('Azure OpenAI endpoint URL.')
output openAiEndpoint string = openAiAccount.properties.endpoint

@description('Name of the OpenAI model deployment.')
output openAiDeploymentName string = modelDeployment.name

@description('Resource ID of the OpenAI account — used by AI Foundry.')
output openAiAccountId string = openAiAccount.id

@description('Primary access key for the Azure OpenAI account — stored in Key Vault for backend use.')
// reason: stored in Key Vault by main.bicep — no alternative to output for cross-module secret passing
#disable-next-line outputs-should-not-contain-secrets
output openAiKey string = openAiAccount.listKeys().key1
