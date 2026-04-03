using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'solune-dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param githubClientId = readEnvironmentVariable('GITHUB_CLIENT_ID', '')
param githubClientSecret = readEnvironmentVariable('GITHUB_CLIENT_SECRET', '')
param sessionSecretKey = readEnvironmentVariable('SESSION_SECRET_KEY', '')
param encryptionKey = readEnvironmentVariable('ENCRYPTION_KEY', '')
param adminGitHubUserId = readEnvironmentVariable('ADMIN_GITHUB_USER_ID', '')
param githubWebhookSecret = readEnvironmentVariable('GITHUB_WEBHOOK_SECRET', '')
param openAiModelName = readEnvironmentVariable('OPENAI_MODEL_NAME', 'gpt-4o')
param deployCapacity = int(readEnvironmentVariable('DEPLOY_CAPACITY', '10'))
