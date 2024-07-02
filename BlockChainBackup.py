import hashlib
import os
import pickle
from datetime import datetime
import time

class Block:
    def __init__(self, index, proof_no, prev_hash, data, timestamp=None):
        self.index = index
        self.proof_no = proof_no
        self.prev_hash = prev_hash
        self.data = data
        self.timestamp = timestamp or time.time()

    @property
    def calculate_hash(self):
        block_string = "{}{}{}{}{}".format(self.index, self.proof_no,
                                           self.prev_hash, self.data,
                                           self.timestamp)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def __repr__(self):
        return "{} - {} - {} - {} - {}".format(self.index, self.proof_no,
                                               self.prev_hash, self.data,
                                               self.timestamp)

class Blockchain:
    def __init__(self, storage_dir='blockchain_data', chunk_size=1, blockchain_name='default'):
        self.chain = []
        self.current_data = []
        self.chunk_index = {}  # Maps block index to chunk file
        self.storage_dir = storage_dir
        self.chunk_size = chunk_size
        self.blockchain_name = blockchain_name
        os.makedirs(self.storage_dir, exist_ok=True)
        self.load_chain()

    def load_chain(self):
        block_files = sorted([f for f in os.listdir(self.storage_dir) if f.startswith(f'{self.blockchain_name}_block_')])
        self.chain = []
        self.chunk_index = {}
        for block_file in block_files:
            with open(os.path.join(self.storage_dir, block_file), 'rb') as file:
                block = pickle.load(file)
                self.chain.append(block)
                self.chunk_index[block.index] = block_file
        if not self.chain:
            self.construct_genesis()

    def save_block(self, block):
        block_file = os.path.join(self.storage_dir, f'{self.blockchain_name}_block_{block.index}.pkl')
        os.makedirs(os.path.dirname(block_file), exist_ok=True)  # Ensure the directory exists
        with open(block_file, 'wb') as file:
            pickle.dump(block, file)
        self.chunk_index[block.index] = block_file

    def construct_genesis(self):
        self.construct_block(proof_no=0, prev_hash='0')

    def construct_block(self, proof_no, prev_hash):
        block = Block(index=len(self.chain),
                      proof_no=proof_no,
                      prev_hash=prev_hash,
                      data=self.current_data)
        self.current_data = []
        self.chain.append(block)
        self.save_block(block)
        return block

    def load_block(self, block_file):
        with open(os.path.join(self.storage_dir, block_file), 'rb') as file:
            return pickle.load(file)

    def load_adjacent_blocks(self, block_index):
        blocks_to_load = set()
        if block_index in self.chunk_index:
            blocks_to_load.add(self.chunk_index[block_index])
        if block_index > 0 and (block_index - 1) in self.chunk_index:
            blocks_to_load.add(self.chunk_index[block_index - 1])
        if (block_index + 1) in self.chunk_index:
            blocks_to_load.add(self.chunk_index[block_index + 1])

        loaded_blocks = []
        for block_file in blocks_to_load:
            loaded_blocks.append(self.load_block(block_file))
        return loaded_blocks

    def verify_block_integrity(self, block):
        if block.index == 0:
            return True  # Genesis block
        prev_block = self.chain[block.index - 1]
        return self.check_validity(block, prev_block)

    def verify_chain_integrity(self, target_block_index):
        loaded_blocks = self.load_adjacent_blocks(target_block_index)
        blocks = {block.index: block for block in loaded_blocks}
        if target_block_index in blocks:
            target_block = blocks[target_block_index]
            prev_block = blocks.get(target_block_index - 1)
            next_block = blocks.get(target_block_index + 1)

            if prev_block and not self.check_validity(target_block, prev_block):
                return False
            if next_block and not self.check_validity(next_block, target_block):
                return False
            return True
        return False

    @staticmethod
    def check_validity(block, prev_block):
        if prev_block.index + 1 != block.index:
            return False
        elif prev_block.calculate_hash != block.prev_hash:
            return False
        elif not Blockchain.verifying_proof(block.proof_no, prev_block.proof_no):
            return False
        return True

    @staticmethod
    def proof_of_work(last_proof):
        proof_no = 0
        while Blockchain.verifying_proof(proof_no, last_proof) is False:
            proof_no += 1
        return proof_no

    @staticmethod
    def verifying_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @property
    def latest_block(self):
        return self.chain[-1]


class FileBlockchain(Blockchain):
    def __init__(self, storage_dir='file_blockchain', chunk_size=1, blockchain_name='default'):
        super().__init__(storage_dir, chunk_size, blockchain_name)
        self.file_index = {}
        self.users = {}
        self.update_file_index()

    def update_file_index(self):
        self.file_index = {}
        for block in self.chain:
            for data in block.data:
                if 'file_name' in data:
                    self.file_index[data['file_name']] = block.index

    def add_file(self, file_path, file_date, file_content, owner, access_blockchain, index_blockchain):
        relative_path = os.path.relpath(file_path, start=os.getcwd())
        self.current_data.append({
            'file_name': relative_path,
            'file_date': file_date,
            'file_content': file_content.hex(),
            'owner': owner
        })
        self.construct_block(self.proof_of_work(self.latest_block.proof_no), self.latest_block.calculate_hash)
        self.update_file_index()

        # Grant access to the owner in the access blockchain
        access_blockchain.grant_access(relative_path, owner, owner)
        access_blockchain.save_access_chain()

        # Update the index blockchain
        index_blockchain.update_index(self.get_file_list())

        print(f"Added file {relative_path} to blockchain.")

    def is_file_in_chain(self, file_name):
        return file_name in self.file_index

    def get_file_content(self, file_name, owner, is_shared=False):
        if file_name not in self.file_index:
            return None
        block_index = self.file_index[file_name]
        if not self.verify_chain_integrity(block_index):
            print("Blockchain integrity check failed.")
            return None
        loaded_blocks = self.load_adjacent_blocks(block_index)
        for block in loaded_blocks:
            for data in block.data:
                if data['file_name'] == file_name and (data['owner'] == owner or is_shared):
                    return bytes.fromhex(data['file_content'])
        return None

    def get_file_list(self):
        file_list = []
        for block in self.chain:
            for data in block.data:
                if 'file_name' in data:
                    file_list.append(
                        {'file_name': data['file_name'], 'owner': data['owner'], 'file_date': data['file_date']})
        return file_list

    def search_files(self, search_word):
        search_results = []
        for block in self.chain:
            for data in block.data:
                if 'file_name' in data and search_word.lower() in data['file_name'].lower():
                    search_results.append(data)
        return search_results

    def register_user(self, username, password):
        if username in self.users:
            return False  # User already exists
        self.users[username] = hashlib.sha256(password.encode()).hexdigest()
        return True

    def authenticate_user(self, username, password):
        if username not in self.users:
            return False
        return self.users[username] == hashlib.sha256(password.encode()).hexdigest()

class AccessBlockchain(Blockchain):
    def __init__(self, storage_dir='access_blockchain', chunk_size=1, blockchain_name='default'):
        super().__init__(storage_dir, chunk_size, blockchain_name)
        self.storage_file = os.path.join(storage_dir, f'{blockchain_name}_access_chain.pkl')
        self.load_access_chain()

    def load_access_chain(self):
        if os.path.exists(self.storage_file):
            with open(self.storage_file, 'rb') as file:
                self.chain = pickle.load(file)
        if not self.chain:
            self.construct_genesis()

    def save_access_chain(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)  # Ensure the directory exists
        with open(self.storage_file, 'wb') as file:
            pickle.dump(self.chain, file)

    def grant_access(self, file_name, owner, user_to_share):
        self.current_data.append({
            'file_name': file_name,
            'owner': owner,
            'user_to_share': user_to_share,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        self.construct_block(self.proof_of_work(self.latest_block.proof_no), self.latest_block.calculate_hash)
        print(f"Granted access to {file_name} for {user_to_share}.")

    def has_access(self, file_name, user):
        for block in self.chain:
            for data in block.data:
                if os.path.basename(data['file_name']) == os.path.basename(file_name) and (data['user_to_share'] == user or data['owner'] == user):
                    return True
        return False

class IndexBlockchain(Blockchain):
    def __init__(self, storage_dir='index_blockchain', num_chunks=1, blockchain_name='default'):
        super().__init__(storage_dir, num_chunks, blockchain_name)

    def update_index(self, file_list):
        self.current_data.append({
            'file_list': file_list,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        self.construct_block(self.proof_of_work(self.latest_block.proof_no), self.latest_block.calculate_hash)
        print("Updated index blockchain with the latest file list.")

    def get_latest_index(self):
        if self.chain:
            return self.chain[-1].data
        return []


def execute_command(command, file_blockchain, access_blockchain, index_blockchain, current_user):
    parts = command.strip().split()
    action = parts[0]

    if action == 'register':
        username = parts[1]
        password = parts[2]
        if file_blockchain.register_user(username, password):
            print(f"User {username} registered successfully.")
        else:
            print(f"User {username} already exists.")

    elif action == 'login':
        if len(parts) != 3:
            print("Enter a username and password to login.")
        else:
            username = parts[1]
            password = parts[2]
            if file_blockchain.authenticate_user(username, password):
                current_user[0] = username
                print(f"User {username} logged in successfully.")
            else:
                print("Invalid username or password.")

    elif action == 'search':
        if current_user[0]:
            search_word = ' '.join(parts[1:])
            search_results = file_blockchain.search_files(search_word)
            print(f"Search results for '{search_word}':")
            for result in search_results:
                print(f"File Name: {result['file_name']}, Owner: {result['owner']}, Date: {result['file_date']}")
        else:
            print("Please log in to search files.")

    elif action == 'backup':

        if len(parts) > 1:
            if current_user[0] is not None:
                blockchain_name = parts[1]
                file_blockchain.blockchain_name = blockchain_name
                access_blockchain.blockchain_name = blockchain_name
                index_blockchain.blockchain_name = blockchain_name

                directory_to_add = '.'  # Specify the directory with files to add
                for root, _, files in os.walk(directory_to_add):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not file_blockchain.is_file_in_chain(file_path):
                            # Exclude files in blockchain storage directories
                            if any(sub_dir in file_path for sub_dir in
                                   ['file_blockchain', 'access_blockchain', 'index_blockchain', 'extracted']):
                                continue
                            file_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                            try:
                                with open(file_path, 'rb') as file_content:
                                    content = file_content.read()
                            except Exception as e:
                                print(f"Skipping file {file_path} due to error: {e}")
                                continue
                            file_blockchain.add_file(file_path, file_date, content, current_user[0], access_blockchain,
                                                     index_blockchain)

                file_blockchain.update_file_index()
                file_blockchain.load_chain()
                print(f"Backup of {blockchain_name} blockchain completed.")
            else:
                print("Please log in to backup files.")
        else:
            print('Enter a name for the backup')
    elif action == 'load_backup':
        if parts[1]:
            blockchain_name = parts[1]
            backup_dir = 'file_blockchain' # Directory where backup blocks are stored
            file_blockchain.blockchain_name = blockchain_name
            access_blockchain.blockchain_name = blockchain_name
            index_blockchain.blockchain_name = blockchain_name

            block_files = sorted([f for f in os.listdir(backup_dir) if f.startswith(f'{blockchain_name}_block_')])
            for block_file in block_files:
                block_path = os.path.join(backup_dir, block_file)
                with open(block_path, 'rb') as file:
                    block = pickle.load(file)
                    file_blockchain.chain.append(block)
                    file_blockchain.chunk_index[block.index] = block_path

            file_blockchain.update_file_index()
            file_blockchain.load_chain()
            print(f"Loaded backup from {blockchain_name} into blockchain.")

    elif action == 'get_file':
        if current_user[0]:
            file_name = parts[1]
            output_name = parts[2]
            if file_blockchain.is_file_in_chain(file_name):
                if access_blockchain.has_access(file_name, current_user[0]):
                    content = file_blockchain.get_file_content(file_name, file_blockchain.users[current_user[0]],
                                                               is_shared=True)
                    if content:

                        with open(output_name, 'wb') as output_file:
                            output_file.write(content)
                        print(f'Content of {file_name} saved to {output_name}')
                    else:
                        print(f'User {current_user[0]} does not have access to {file_name}')
                else:
                    print(f'File {file_name} access not granted')
            else:
                print('File does not exist in the blockchain')
        else:
            print("Please log in to get files.")

    elif action == 'grant_permission':
        if current_user[0]:
            path_to_grant = parts[1]
            user_to_grant = parts[2]
            if os.path.isdir(path_to_grant):
                for root, _, files in os.walk(path_to_grant):
                    for file in files:
                        relative_file_path = os.path.relpath(os.path.join(root, file), start=os.getcwd())
                        if file_blockchain.is_file_in_chain(relative_file_path):
                            access_blockchain.grant_access(relative_file_path, current_user[0], user_to_grant)
                            access_blockchain.save_access_chain()
                            print(f"Access to {relative_file_path} granted to {user_to_grant}")
                        else:
                            print(f"File {relative_file_path} does not exist in the blockchain")
            else:
                if file_blockchain.is_file_in_chain(path_to_grant):
                    access_blockchain.grant_access(path_to_grant, current_user[0], user_to_grant)
                    access_blockchain.save_access_chain()
                    print(f"Access to {path_to_grant} granted to {user_to_grant}")
                else:
                    print("File does not exist in the blockchain")
        else:
            print("Please log in to grant permission.")

    elif action == 'get_all':
        if current_user[0]:
            file_blockchain.load_chain()
            output_dir = 'extracted'
            os.makedirs(output_dir, exist_ok=True)
            file_list = file_blockchain.get_file_list()
            for file in file_list:
                file_name = file['file_name']
                if access_blockchain.has_access(file_name, current_user[0]):
                    content = file_blockchain.get_file_content(file_name, current_user[0])
                    if content:
                        output_path = os.path.join(output_dir, file_name)
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'wb') as output_file:
                            output_file.write(content)
                        print(f'Extracted {file_name} to {output_path}')
                    else:
                        print(f'User {current_user[0]} does not have access to {file_name}')
                else:
                    print(f'File {file_name} access not granted')
        else:
            print("Please log in to get all files.")


if __name__ == '__main__':
    NUM_CHUNKS = 1  # Example number of chunks, you can change this value
    BLOCKCHAIN_NAME = 'default'

    file_blockchain = FileBlockchain(blockchain_name=BLOCKCHAIN_NAME)
    access_blockchain = AccessBlockchain(blockchain_name=BLOCKCHAIN_NAME)
    index_blockchain = IndexBlockchain(blockchain_name=BLOCKCHAIN_NAME)

    # Register users
    if not file_blockchain.authenticate_user('DisD', 'DisD43v3r'):
        file_blockchain.register_user('DisD', 'DisD43v3r')
    if not file_blockchain.authenticate_user('bob', 'password456'):
        file_blockchain.register_user('bob', 'password456')

    # Update the index blockchain with the latest file list
    index_blockchain.update_index(file_blockchain.get_file_list())

    current_user = [None]  # Placeholder for the current logged-in user

    # Main loop to handle commands
    while True:
        command = input("Enter command (register <username> <password>, login <username> <password>,\n"
                        "search <words>, backup <blockchain> <num_chunks>, get_file <file-name> <output-name>,\n"
                        "get_all, grant_permission <file_name> <user_granted>, load_backup <backup_directory>, exit): ")
        if command == 'exit':
            break
        execute_command(command, file_blockchain, access_blockchain, index_blockchain, current_user)
