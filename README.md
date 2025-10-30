# DaggerheartCodex

DaggerheartCodex is a Python Flask application for finding and managing Adversaries and Environments cards for the Daggerheart roleplaying game. It allows for the updating of existing cards and the creation of new ones, and it comes pre-loaded with the Daggerheart Systems Reference Document (SRD).

## Features

*   Find and manage Adversaries and Environments cards.
*   Update existing cards.
*   Create new cards based on their names.
*   Comes pre-loaded with the Daggerheart SRD.

## Getting Started

To get started with the DaggerheartCodex, you can either clone the repository or download the ZIP file.

### Prerequisites

*   Python 3.x
*   pip

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mabrown666/DaggerheartCodex.git
    cd DaggerheartCodex
    ```
    **OR**
    **Download the ZIP file:**
    Download the ZIP file from the [main repository page](https://github.com/mabrown666/DaggerheartCodex) and extract it.

2.  **Install the required dependencies using pip:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

To run the application, execute the following command from the project's root directory:
```bash
python -m app
```
Once the application is running, you can access it in your web browser at the following URL:
[http://127.0.0.1:8282](http://127.0.0.1:8282)

## Usage

Once the application is running, you can use the web interface to:
*   **Search for cards:** Use the search bar to find specific Adversaries or Environments cards.
*   **View card details:** Click on a card to view its details.
*   **Edit cards:** Click the "Edit" button on a card's detail page to modify its contents.
*   **Create new cards:** Use the "Create New" feature to add new cards to the codex.

## API Documentation

The Daggerheart Codex has some basic API for intergrarion into other programs. See [API Documentation](api.md) for details.


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.