
# Blockchain Backup System

A secure, immutable backup solution using blockchain technology for tamper-proof file storage and transparent file history.

## Features

- Immutable file storage
- Secure and transparent file history
- Local blockchain implementation

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/blockchain-backup.git
   cd blockchain-backup
   ```

2. Ensure you have Python installed, then install the required packages (if any).

## Usage

1. Run the script:
   ```bash
   python BlockChainBackup.py
   ```

2. Use the following commands within the program:

   - **Register a new user**:
     ```bash
     register <username> <password>
     ```

   - **Login as an existing user**:
     ```bash
     login <username> <password>
     ```

   - **Search for files**:
     ```bash
     search <words>
     ```

   - **Backup files to the blockchain**:
     ```bash
     backup <blockchain_name>
     ```

   - **Load a backup from the blockchain**:
     ```bash
     load_backup <blockchain_name>
     ```

   - **Retrieve a file from the blockchain**:
     ```bash
     get_file <file-name> <output-name>
     ```

   - **Grant access to a file for another user**:
     ```bash
     grant_permission <file_name> <user_granted>
     ```

   - **Retrieve all accessible files**:
     ```bash
     get_all
     ```

3. To exit the program, type:
   ```bash
   exit
   ```

## Example

1. Register a user:
   ```bash
   register alice password123
   ```

2. Login as the user:
   ```bash
   login alice password123
   ```

3. Backup files to the blockchain:
   ```bash
   backup my_backup
   ```

4. Retrieve a file from the blockchain:
   ```bash
   get_file path/to/file.txt output_file.txt
   ```

5. Grant access to a file:
   ```bash
   grant_permission path/to/file.txt bob
   ```

6. Retrieve all accessible files:
   ```bash
   get_all
   ```

## Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for more details.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
