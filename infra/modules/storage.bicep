@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Principal ID of the managed identity — granted Storage File Data SMB Share Contributor role.')
param identityPrincipalId string

@description('Storage Account (StorageV2, Standard_LRS) for Azure Files shares.')
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: replace('st${environmentName}', '-', '')
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
  }
}

@description('File service for the storage account.')
resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

@description('Azure Files share for Solune SQLite database persistence (1 GiB).')
resource soluneDataShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'solune-data'
  properties: {
    shareQuota: 1
  }
}

@description('Azure Files share for Signal CLI configuration (1 GiB).')
resource signalConfigShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'signal-config'
  properties: {
    shareQuota: 1
  }
}

@description('Storage File Data SMB Share Contributor role definition.')
var storageSmbContributorRoleId = '0c867c2a-1d8c-454a-a3db-ab2ea1bdc8bb'

@description('Assigns Storage File Data SMB Share Contributor role to the managed identity.')
resource storageSmbRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, identityPrincipalId, storageSmbContributorRoleId)
  scope: storageAccount
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageSmbContributorRoleId)
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the storage account.')
output storageAccountName string = storageAccount.name

@description('Resource ID of the storage account — used by AI Foundry.')
output storageAccountId string = storageAccount.id

@description('Access key for the storage account — used by Container Apps for Azure Files volume mounts.')
#disable-next-line outputs-should-not-contain-secrets
output storageAccountKey string = storageAccount.listKeys().keys[0].value
