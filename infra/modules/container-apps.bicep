@description('Name of the azd environment — used as a prefix for all resource names.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Resource ID of the user-assigned managed identity.')
param identityId string

@description('Client ID of the user-assigned managed identity — used for DefaultAzureCredential.')
param identityClientId string

@description('Login server URL for the Azure Container Registry.')
param registryLoginServer string

@description('Log Analytics Workspace customer ID for Container Apps Environment.')
param workspaceCustomerId string

@secure()
@description('Log Analytics Workspace shared key for Container Apps Environment.')
param workspaceSharedKey string

@description('Name of the Key Vault — used for secret references.')
param vaultName string

@description('Azure OpenAI endpoint URL.')
param openAiEndpoint string

@description('Name of the Azure OpenAI model deployment.')
param openAiDeploymentName string

@description('Name of the storage account — used for Azure Files volume mounts.')
param storageAccountName string

@secure()
@description('Storage account access key — used for Azure Files volume mounts.')
param storageAccountKey string

@description('Admin GitHub user ID — passed to backend as ADMIN_GITHUB_USER_ID.')
param adminGitHubUserId string

@description('Container Apps Environment with managed VNet and Log Analytics integration.')
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${environmentName}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspaceCustomerId
        sharedKey: workspaceSharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

@description('Azure Files storage mount for solune-data share (SQLite persistence).')
resource soluneDataStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: containerAppsEnvironment
  name: 'solune-data'
  properties: {
    azureFile: {
      accountName: storageAccountName
      accountKey: storageAccountKey
      shareName: 'solune-data'
      accessMode: 'ReadWrite'
    }
  }
}

@description('Azure Files storage mount for signal-config share (Signal CLI state).')
resource signalConfigStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: containerAppsEnvironment
  name: 'signal-config'
  properties: {
    azureFile: {
      accountName: storageAccountName
      accountKey: storageAccountKey
      shareName: 'signal-config'
      accessMode: 'ReadWrite'
    }
  }
}

@description('Backend Container App — FastAPI service with Key Vault refs, Azure Files, and managed identity.')
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-backend-${environmentName}'
  location: location
  tags: union(tags, { 'azd-service-name': 'backend' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
        allowInsecure: true
      }
      registries: [
        {
          server: registryLoginServer
          identity: identityId
        }
      ]
      secrets: [
        {
          name: 'github-client-id'
          keyVaultUrl: 'https://${vaultName}${environment().suffixes.keyvaultDns}/secrets/github-client-id'
          identity: identityId
        }
        {
          name: 'github-client-secret'
          keyVaultUrl: 'https://${vaultName}${environment().suffixes.keyvaultDns}/secrets/github-client-secret'
          identity: identityId
        }
        {
          name: 'session-secret-key'
          keyVaultUrl: 'https://${vaultName}${environment().suffixes.keyvaultDns}/secrets/session-secret-key'
          identity: identityId
        }
        {
          name: 'encryption-key'
          keyVaultUrl: 'https://${vaultName}${environment().suffixes.keyvaultDns}/secrets/encryption-key'
          identity: identityId
        }
        {
          name: 'github-webhook-secret'
          keyVaultUrl: 'https://${vaultName}${environment().suffixes.keyvaultDns}/secrets/github-webhook-secret'
          identity: identityId
        }
        {
          name: 'azure-openai-key'
          keyVaultUrl: 'https://${vaultName}${environment().suffixes.keyvaultDns}/secrets/azure-openai-key'
          identity: identityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${registryLoginServer}/solune-backend:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'GITHUB_CLIENT_ID', secretRef: 'github-client-id' }
            { name: 'GITHUB_CLIENT_SECRET', secretRef: 'github-client-secret' }
            { name: 'SESSION_SECRET_KEY', secretRef: 'session-secret-key' }
            { name: 'ENCRYPTION_KEY', secretRef: 'encryption-key' }
            { name: 'GITHUB_WEBHOOK_SECRET', secretRef: 'github-webhook-secret' }
            { name: 'AZURE_OPENAI_KEY', secretRef: 'azure-openai-key' }
            { name: 'AI_PROVIDER', value: 'azure_openai' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiDeploymentName }
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
            { name: 'SIGNAL_API_URL', value: 'https://${signalApiApp.properties.configuration.ingress.fqdn}' }
            { name: 'FRONTEND_URL', value: 'https://${frontendApp.properties.configuration.ingress.fqdn}' }
            { name: 'CORS_ORIGINS', value: 'https://${frontendApp.properties.configuration.ingress.fqdn}' }
            { name: 'COOKIE_SECURE', value: 'true' }
            { name: 'DATABASE_PATH', value: '/var/lib/solune/data/settings.db' }
            { name: 'HOST', value: '0.0.0.0' }
            { name: 'PORT', value: '8000' }
            { name: 'DEBUG', value: 'false' }
            { name: 'ADMIN_GITHUB_USER_ID', value: adminGitHubUserId }
          ]
          volumeMounts: [
            {
              volumeName: 'solune-data'
              mountPath: '/var/lib/solune/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/v1/health'
                port: 8000
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/v1/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
      volumes: [
        {
          name: 'solune-data'
          storageType: 'AzureFile'
          storageName: soluneDataStorage.name
        }
      ]
    }
  }
}

@description('Frontend Container App — React/nginx with external ingress.')
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-frontend-${environmentName}'
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
      }
      registries: [
        {
          server: registryLoginServer
          identity: identityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${registryLoginServer}/solune-frontend:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'BACKEND_ORIGIN', value: 'http://ca-backend-${environmentName}.internal.${containerAppsEnvironment.properties.defaultDomain}' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

@description('Signal API Container App — signal-cli-rest-api with internal ingress and Azure Files volume.')
resource signalApiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-signal-${environmentName}'
  location: location
  tags: union(tags, { 'azd-service-name': 'signal-api' })
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8080
        transport: 'http'
        allowInsecure: true
      }
    }
    template: {
      containers: [
        {
          name: 'signal-api'
          image: 'docker.io/bbernhard/signal-cli-rest-api:0.98'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'MODE', value: 'json-rpc' }
            { name: 'DEFAULT_SIGNAL_TEXT_MODE', value: 'styled' }
          ]
          volumeMounts: [
            {
              volumeName: 'signal-config'
              mountPath: '/home/.local/share/signal-cli'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/v1/health'
                port: 8080
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/v1/health'
                port: 8080
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'signal-config'
          storageType: 'AzureFile'
          storageName: signalConfigStorage.name
        }
      ]
    }
  }
}

@description('External FQDN of the frontend Container App.')
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn

@description('Internal FQDN of the backend Container App.')
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn

@description('Internal FQDN of the Signal API Container App.')
output signalApiFqdn string = signalApiApp.properties.configuration.ingress.fqdn
