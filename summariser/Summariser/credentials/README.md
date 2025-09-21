# Google Cloud Credentials

Place your Google Cloud service account JSON file in this directory.

## Setup Instructions:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `iconic-ruler-472218-g3`
3. Navigate to "IAM & Admin" > "Service Accounts"
4. Create a new service account or use an existing one
5. Grant the following roles:
   - Vertex AI User
   - Cloud Speech API User  
   - Document AI API User
   - Storage Object Admin (if using Cloud Storage)
6. Create and download a JSON key file
7. Save it as `service-account.json` in this directory
8. Update the `.env` file to point to: `./service-account.json`

## Required APIs to Enable:

- Vertex AI API
- Cloud Speech-to-Text API
- Document AI API
- Cloud Storage API (optional)

You can enable these APIs in the [Google Cloud Console API Library](https://console.cloud.google.com/apis/library).
