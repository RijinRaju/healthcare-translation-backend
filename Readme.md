# Healthcare Translation App - Backend

Welcome to the backend repository for the **Healthcare Translation App**. This application is designed to facilitate seamless communication in healthcare settings by providing accurate and reliable translations.

## Features

- **Real-time Translation**: Supports multiple languages for instant communication.
- **Medical Terminology Support**: Specialized translations for healthcare-specific terms.
- **Secure API**: Ensures data privacy and security.
- **Scalable Architecture**: Built to handle high traffic and multiple users.

## Prerequisites

- **FastAPI** 
- **Deepgram (Audio transcription)**
- **Claude AI (Audio translation)**
- **Environment Variables**:
    - `API_KEY`: API key for external translation services

## Installation

1. Clone the repository:
     ```bash
     git clone https://github.com/RijinRaju/healthcare-translation-backend.git
     cd healthcare-translation-app-backend
     ```

2. Install dependencies:
     ```bash
     npm install
     ```

3. Set up environment variables:
     Create a `.env` file in the root directory and add the required variables.

4. Start the server:
     ```bash
     npm start
     ```

## API Endpoints

| Method | Endpoint         | Description                                     |
|--------|------------------|-------------------------------------------------|
| ws     | `/ws/transcribe` | Get realtime transcription and translations.    |


## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m "Add feature"`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For questions or support, please contact:
- **Email**: support@healthcaretranslator.com
- **GitHub Issues**: [Issue Tracker](https://github.com/RijinRaju/healthcare-translation-backend/issues)
