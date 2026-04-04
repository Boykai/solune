@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('User-assigned managed identity shared by backend services for accessing Key Vault, ACR, OpenAI, AI Foundry, and Storage.')
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${environmentName}'
  location: location
  tags: tags
}

@description('Resource ID of the managed identity.')
output identityId string = managedIdentity.id

@description('Principal ID of the managed identity — used for RBAC role assignments.')
output identityPrincipalId string = managedIdentity.properties.principalId

@description('Client ID of the managed identity — used in Container App configuration.')
output identityClientId string = managedIdentity.properties.clientId
