@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Log Analytics Workspace for centralized logging and diagnostics.')
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'law-${environmentName}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

@description('Application Insights for application performance monitoring.')
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-${environmentName}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
  }
}

@description('Resource ID of the Log Analytics Workspace.')
output workspaceId string = logAnalyticsWorkspace.id

@description('Customer ID of the Log Analytics Workspace — used by Container Apps Environment.')
output workspaceCustomerId string = logAnalyticsWorkspace.properties.customerId

@description('Shared key for the Log Analytics Workspace — used by Container Apps Environment.')
// reason: required by Container Apps Environment module — consumed as secureParam in container-apps.bicep
#disable-next-line outputs-should-not-contain-secrets
output workspaceSharedKey string = logAnalyticsWorkspace.listKeys().primarySharedKey

@description('Application Insights connection string for telemetry.')
output appInsightsConnectionString string = appInsights.properties.ConnectionString

@description('Resource ID of the Application Insights instance — used by AI Foundry.')
output appInsightsId string = appInsights.id
