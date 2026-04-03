@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Principal ID of the managed identity — granted AcrPull role.')
param identityPrincipalId string

@description('Azure Container Registry for hosting container images (Basic SKU, admin disabled).')
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('${environmentName}acr', '-', '')
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

@description('AcrPull role definition — allows pulling images from the registry.')
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

@description('Assigns AcrPull role to the managed identity on the container registry.')
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, identityPrincipalId, acrPullRoleId)
  scope: containerRegistry
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the container registry.')
output registryName string = containerRegistry.name

@description('Login server URL for the container registry.')
output registryLoginServer string = containerRegistry.properties.loginServer
