  # Set variables
  RESOURCE_GROUP="jmotylinski-sandbox"
  LOCATION="eastus"
  APP_NAME="gh-productivity"  # Must be globally unique

  # Create resource group
  az group create --name $RESOURCE_GROUP --location $LOCATION

  # Create App Service plan (B1 is basic paid tier, F1 is free)
  az appservice plan create \
    --name "${APP_NAME}-plan" \
    --resource-group $RESOURCE_GROUP \
    --sku F1 \
    --is-linux

  # Create the web app
  az webapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan "${APP_NAME}-plan" \
    --runtime "PYTHON:3.11"
