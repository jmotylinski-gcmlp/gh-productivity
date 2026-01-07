#!/bin/bash
set -e
export AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1

# Set variables (must match create.sh)
RESOURCE_GROUP="jmotylinski-sandbox"
APP_NAME="gh-productivity"

# Configure startup command and health check
echo "Configuring startup command and health check..."
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 src.app:app" \
  --generic-configurations '{"healthCheckPath": "/api/admin/health"}'

# Set environment variables
echo "Setting app configuration..."
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true \
             PYTHONPATH="."

# Create deployment package (exclude unnecessary files)
echo "Creating deployment package..."
zip -r deploy.zip . \
  -x "*.git*" \
  -x "venv/*" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "data/raw/*" \
  -x ".env" \
  -x "deploy.zip" \
  -x "*.sh"

# Deploy the zip file
echo "Deploying to Azure..."
az webapp deployment source config-zip \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --src deploy.zip

# Clean up
rm deploy.zip

echo ""
echo "Deployment complete!"
echo "App URL: https://${APP_NAME}.azurewebsites.net"
echo ""
echo "To enable scheduled data fetching, configure these App Settings:"
echo "  az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME \\"
echo "    --settings GITHUB_TOKEN=<token> JIRA_EMAIL=<email> JIRA_API_TOKEN=<token> ADMIN_API_KEY=<secret>"
echo ""
echo "Then set up a scheduler (Azure Logic Apps, GitHub Actions, etc.) to call:"
echo "  POST https://${APP_NAME}.azurewebsites.net/api/admin/fetch"
echo "  Header: X-API-Key: <your ADMIN_API_KEY>"
