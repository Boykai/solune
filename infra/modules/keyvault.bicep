@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Principal ID of the managed identity — granted Key Vault Secrets User role.')
param identityPrincipalId string

@description('GitHub OAuth App Client ID — stored as a Key Vault secret.')
param githubClientId string

@secure()
@description('GitHub OAuth App Client Secret — stored as a Key Vault secret.')
param githubClientSecret string

@secure()
@description('Session encryption key (64+ character hex string) — stored as a Key Vault secret.')
param sessionSecretKey string

@secure()
@description('Fernet encryption key for token-at-rest encryption — stored as a Key Vault secret.')
param encryptionKey string

@secure()
@description('GitHub Webhook secret for verifying webhook payloads — stored as a Key Vault secret.')
param githubWebhookSecret string

@secure()
@description('Azure OpenAI API key — stored as a Key Vault secret for backend use.')
param azureOpenAiKey string

@description('Azure Key Vault with RBAC authorization, purge protection, and 90-day soft-delete.')
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${environmentName}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
}

@description('Stores GitHub Client ID in Key Vault.')
resource secretGitHubClientId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'github-client-id'
  properties: {
    value: githubClientId
  }
}

@description('Stores GitHub Client Secret in Key Vault.')
resource secretGitHubClientSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'github-client-secret'
  properties: {
    value: githubClientSecret
  }
}

@description('Stores session secret key in Key Vault.')
resource secretSessionSecretKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'session-secret-key'
  properties: {
    value: sessionSecretKey
  }
}

@description('Stores encryption key in Key Vault.')
resource secretEncryptionKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'encryption-key'
  properties: {
    value: encryptionKey
  }
}

@description('Stores GitHub webhook secret in Key Vault.')
resource secretGitHubWebhookSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'github-webhook-secret'
  properties: {
    value: githubWebhookSecret
  }
}

@description('Stores Azure OpenAI API key in Key Vault.')
resource secretAzureOpenAiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-openai-key'
  properties: {
    value: azureOpenAiKey
  }
}

@description('Key Vault Secrets User role definition — allows reading secrets.')
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

@description('Assigns Key Vault Secrets User role to the managed identity.')
resource kvSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, identityPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the Key Vault.')
output vaultName string = keyVault.name

@description('URI of the Key Vault.')
output vaultUri string = keyVault.properties.vaultUri

@description('Resource ID of the Key Vault — used by AI Foundry.')
output vaultId string = keyVault.id
