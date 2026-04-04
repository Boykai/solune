@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Principal ID of the managed identity — granted Azure AI Developer role.')
param identityPrincipalId string

@description('Resource ID of the Azure OpenAI account — linked as AI Services connection.')
param openAiAccountId string

@description('Resource ID of the Key Vault — linked to AI Foundry Hub.')
param keyVaultId string

@description('Resource ID of the Storage Account — linked to AI Foundry Hub.')
param storageAccountId string

@description('Resource ID of the Application Insights instance — linked to AI Foundry Hub.')
param appInsightsId string

@description('AI Foundry Hub — central management workspace for AI resources.')
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: 'aih-${environmentName}'
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: 'Solune AI Hub (${environmentName})'
    keyVault: keyVaultId
    storageAccount: storageAccountId
    applicationInsights: appInsightsId
  }
}

@description('AI Services connection to Azure OpenAI — links the OpenAI account to the Hub.')
resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-10-01' = {
  parent: aiHub
  name: 'aoai-connection'
  properties: {
    category: 'AzureOpenAI'
    target: openAiAccountId
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: openAiAccountId
    }
  }
}

@description('AI Foundry Project — feature-specific workspace linked to the Hub.')
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: 'aip-${environmentName}'
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: 'Solune AI Project (${environmentName})'
    hubResourceId: aiHub.id
  }
}

@description('Azure AI Developer role definition — allows access to AI Foundry projects.')
var azureAIDeveloperRoleId = '64702f94-c441-49e6-a78b-ef80e0188fee'

@description('Assigns Azure AI Developer role to the managed identity on the AI Project.')
resource aiDeveloperRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, identityPrincipalId, azureAIDeveloperRoleId)
  scope: aiProject
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIDeveloperRoleId)
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the AI Foundry Hub.')
output hubName string = aiHub.name

@description('Name of the AI Foundry Project.')
output projectName string = aiProject.name
