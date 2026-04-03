targetScope = 'resourceGroup'

// ─── Parameters ─────────────────────────────────────────────────────────────

@minLength(1)
@maxLength(64)
@description('Name of the azd environment — used as a prefix for all resource names and the azd-env-name tag.')
param environmentName string

@description('Azure region for all resources. Must support Azure Container Apps, Azure OpenAI, and Azure AI Foundry.')
param location string = resourceGroup().location

@description('GitHub OAuth App Client ID.')
param githubClientId string

@secure()
@description('GitHub OAuth App Client Secret — stored in Key Vault, never exposed in container env vars.')
param githubClientSecret string

@secure()
@description('Session encryption key (64+ character hex string).')
param sessionSecretKey string

@secure()
@description('Fernet encryption key for token-at-rest encryption.')
param encryptionKey string

@description('Numeric GitHub user ID of the admin account.')
param adminGitHubUserId string

@description('Name for the Azure OpenAI model deployment.')
param openAiModelName string = 'gpt-4o'

@description('Azure OpenAI deployment capacity in thousands of tokens per minute.')
param deployCapacity int = 10

// ─── Tags ───────────────────────────────────────────────────────────────────

var tags = {
  'azd-env-name': environmentName
}

// ─── Module: Managed Identity ───────────────────────────────────────────────

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// ─── Module: Monitoring (Log Analytics + Application Insights) ──────────────

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// ─── Module: Container Registry ─────────────────────────────────────────────

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.identityPrincipalId
  }
}

// ─── Module: Key Vault ──────────────────────────────────────────────────────

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.identityPrincipalId
    githubClientId: githubClientId
    githubClientSecret: githubClientSecret
    sessionSecretKey: sessionSecretKey
    encryptionKey: encryptionKey
  }
}

// ─── Module: Azure OpenAI ───────────────────────────────────────────────────

module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.identityPrincipalId
    openAiModelName: openAiModelName
    deployCapacity: deployCapacity
  }
}

// ─── Module: Storage Account + Azure Files ──────────────────────────────────

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.identityPrincipalId
  }
}

// ─── Module: AI Foundry Hub + Project ───────────────────────────────────────

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.identityPrincipalId
    openAiAccountId: openai.outputs.openAiAccountId
    keyVaultId: keyvault.outputs.vaultId
    storageAccountId: storage.outputs.storageAccountId
    appInsightsId: monitoring.outputs.appInsightsId
  }
}

// ─── Module: Container Apps Environment + 3 Apps ────────────────────────────

module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    identityId: identity.outputs.identityId
    identityClientId: identity.outputs.identityClientId
    registryLoginServer: registry.outputs.registryLoginServer
    workspaceCustomerId: monitoring.outputs.workspaceCustomerId
    workspaceSharedKey: monitoring.outputs.workspaceSharedKey
    vaultName: keyvault.outputs.vaultName
    openAiEndpoint: openai.outputs.openAiEndpoint
    openAiDeploymentName: openai.outputs.openAiDeploymentName
    storageAccountName: storage.outputs.storageAccountName
    storageAccountKey: storage.outputs.storageAccountKey
    adminGitHubUserId: adminGitHubUserId
  }
}

// ─── Outputs ────────────────────────────────────────────────────────────────

@description('External FQDN of the frontend Container App — primary user-facing URL.')
output frontendUrl string = 'https://${containerApps.outputs.frontendFqdn}'

@description('Internal FQDN of the backend Container App.')
output backendInternalUrl string = 'https://${containerApps.outputs.backendFqdn}'

@description('Internal FQDN of the Signal API Container App.')
output signalApiInternalUrl string = 'https://${containerApps.outputs.signalApiFqdn}'

@description('Name of the resource group.')
output resourceGroupName string = resourceGroup().name

@description('Name of the Azure Container Registry.')
output containerRegistryName string = registry.outputs.registryName

@description('Login server URL for the ACR.')
output containerRegistryLoginServer string = registry.outputs.registryLoginServer

@description('Name of the Key Vault.')
output keyVaultName string = keyvault.outputs.vaultName

@description('Azure OpenAI endpoint URL.')
output openAiEndpoint string = openai.outputs.openAiEndpoint

@description('Name of the OpenAI model deployment.')
output openAiDeploymentName string = openai.outputs.openAiDeploymentName

@description('Client ID of the managed identity.')
output managedIdentityClientId string = identity.outputs.identityClientId

@description('Resource ID of the Log Analytics Workspace.')
output logAnalyticsWorkspaceId string = monitoring.outputs.workspaceId

@description('Application Insights connection string.')
output applicationInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString

@description('Name of the AI Foundry Hub.')
output aiFoundryHubName string = aiFoundry.outputs.hubName

@description('Name of the AI Foundry Project.')
output aiFoundryProjectName string = aiFoundry.outputs.projectName

@description('OAuth callback URL — configure in GitHub OAuth App after deployment.')
output oauthCallbackUrl string = 'https://${containerApps.outputs.frontendFqdn}/api/v1/auth/github/callback'
