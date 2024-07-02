import hashlib
import os
import pickle
import time
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

class Block:
    def __init__(self, index, proof_no, prev_hash, data, timestamp=None):
        self.index = index
        self.proof_no = proof_no
        self.prev_hash = prev_hash
        self.data = data
        self.timestamp = timestamp or time.time()

    @property
    def calculate_hash(self):
        block_string = "{}{}{}{}{}".format(self.index, self.proof_no, self.prev_hash, self.data, self.timestamp)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def __repr__(self):
        return "{} - {} - {} - {} - {}".format(self.index, self.proof_no, self.prev_hash, self.data, self.timestamp)

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
        def extract_block_index(filename):
            return int(filename.split('_block_')[-1].split('.')[0])

        block_files = sorted(
            [f for f in os.listdir(self.storage_dir) if f.startswith(f'{self.blockchain_name}_block_')],
            key=extract_block_index
        )

        self.chain = []
        self.chunk_index = {}

        for block_file in block_files:
            with open(os.path.join(self.storage_dir, block_file), 'rb') as file:
                block = pickle.load(file)
                if self.chain and not self.check_validity(block, self.chain[-1]):
                    print(f"Integrity check failed when loading block {block.index}.")
                    print(f"Expected Prev Hash: {self.chain[-1].calculate_hash}, Found Prev Hash: {block.prev_hash}")
                    raise ValueError(f"Integrity check failed when loading block {block.index}.")
                self.chain.append(block)
                self.chunk_index[block.index] = block_file
                print(block.index)

        if not self.chain:
            self.construct_genesis()

        print("Blockchain loaded successfully. Verifying entire chain integrity...")
        if not self.verify_chain_integrity():
            raise ValueError("Blockchain integrity check failed after loading the chain.")

    def verify_chain_integrity(self):
        print("Verifying entire blockchain integrity...")
        for index in range(1, len(self.chain)):
            prev_block = self.chain[index - 1]
            current_block = self.chain[index]
            if not self.check_validity(current_block, prev_block):
                print(f"Block {current_block.index} has invalid previous hash.")
                print(f"Expected Prev Hash: {prev_block.calculate_hash}")
                print(f"Found Prev Hash: {current_block.prev_hash}")
                return False
        print("Blockchain integrity verified.")
        return True

    @staticmethod
    def check_validity(block, prev_block):
        if prev_block.index + 1 != block.index:
            print(f"Invalid index at block {block.index}")
            return False
        if prev_block.calculate_hash != block.prev_hash:
            print(f"Invalid previous hash at block {block.index}")
            print(f"Expected: {prev_block.calculate_hash}, Found: {block.prev_hash}")
            return False
        if not Blockchain.verifying_proof(block.proof_no, prev_block.proof_no):
            print(f"Invalid proof of work at block {block.index}")
            return False
        return True

    @staticmethod
    def proof_of_work(last_proof):
        proof_no = 0
        while not Blockchain.verifying_proof(proof_no, last_proof):
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

    def save_block(self, block):
        block_file = os.path.join(self.storage_dir, f'{self.blockchain_name}_block_{block.index}.pkl')
        os.makedirs(os.path.dirname(block_file), exist_ok=True)  # Ensure the directory exists
        with open(block_file, 'wb') as file:
            pickle.dump(block, file)
        self.chunk_index[block.index] = block_file

    def construct_genesis(self):
        print("Constructing genesis block")
        self.construct_block(proof_no=0, prev_hash='0')

    def construct_block(self, proof_no, prev_hash):
        # Ensure the index is correct
        expected_index = len(self.chain)
        if self.chain:
            prev_block = self.latest_block
            if prev_block.index + 1 != expected_index:
                raise ValueError(f"Block index mismatch: expected {prev_block.index + 1}, found {expected_index}")

        block = Block(index=expected_index, proof_no=proof_no, prev_hash=prev_hash, data=self.current_data)
        self.current_data = []
        self.chain.append(block)
        self.save_block(block)
        print(f"Constructed block {block.index} with prev_hash {block.prev_hash} and hash {block.calculate_hash}")

        # Verify the chain integrity after adding the new block
        if not self.verify_chain_integrity():
            print(f"Integrity check failed after constructing block {block.index}.")
            raise ValueError(f"Integrity check failed after constructing block {block.index}.")

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
        print(f"Verifying block {block.index} with prev_hash {block.prev_hash} against {prev_block.calculate_hash}")
        return self.check_validity(block, prev_block)

class FileBlockchain(Blockchain):
    def __init__(self, storage_dir='file_blockchain', chunk_size=1, blockchain_name='default'):
        super().__init__(storage_dir, chunk_size, blockchain_name)
        self.file_index = {}
        self.users = {}
        self.update_file_index()
        self.load_users_from_chain()  # Load users from the blockchain

    def update_file_index(self):
        self.file_index = {}
        for block in self.chain:
            for data in block.data:
                if 'file_name' in data:
                    self.file_index[data['file_name']] = block.index

    def load_users_from_chain(self):
        for block in self.chain:
            for data in block.data:
                if 'username' in data and 'password_hash' in data:
                    self.users[data['username']] = data['password_hash']

    def add_user(self, username, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.current_data.append({
            'username': username,
            'password_hash': password_hash
        })
        proof_no = self.proof_of_work(self.latest_block.proof_no)
        self.construct_block(proof_no, self.latest_block.calculate_hash)
        self.users[username] = password_hash

    def register_user(self, username, password):
        if username in self.users:
            return False  # User already exists
        self.add_user(username, password)
        return True

    def authenticate_user(self, username, password):
        if username not in self.users:
            return False
        return self.users[username] == hashlib.sha256(password.encode()).hexdigest()

    def add_file(self, file_path, file_date, file_content, owner, access_blockchain, index_blockchain):
        relative_path = os.path.relpath(file_path, start=os.getcwd())
        self.current_data.append({
            'file_name': relative_path,
            'file_date': file_date,
            'file_content': file_content.hex(),
            'owner': owner
        })
        proof_no = self.proof_of_work(self.latest_block.proof_no)
        new_block = self.construct_block(proof_no, self.latest_block.calculate_hash)
        self.update_file_index()

        # Grant access to the owner in the access blockchain
        access_blockchain.grant_access(relative_path, owner, owner)
        access_blockchain.save_access_chain()

        # Update the index blockchain
        index_blockchain.update_index(self.get_file_list())

        print(f"Added file {relative_path} to blockchain as block {new_block.index}")

    def is_file_in_chain(self, file_name):
        return file_name in self.file_index

    def get_file_content(self, file_name, owner, is_shared=False):
        if file_name not in self.file_index:
            return None
        block_index = self.file_index[file_name]
        if not self.verify_chain_integrity():
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
                    file_list.append({'file_name': data['file_name'], 'owner': data['owner'], 'file_date': data['file_date']})
        return file_list

    def search_files(self, search_word):
        search_results = []
        for block in self.chain:
            for data in block.data:
                if 'file_name' in data and search_word.lower() in data['file_name'].lower():
                    search_results.append(data)
        return search_results

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


class BlockchainApp(App):
    def build(self):

        self.current_user = [None]

        self.main_layout = BoxLayout(orientation='vertical')

        self.username_input = TextInput(hint_text='Username')
        self.password_input = TextInput(hint_text='Password', password=True)
        self.command_input = TextInput(hint_text='Command')
        self.blockchain_name_input = TextInput(hint_text='Blockchain Name')

        self.main_layout.add_widget(self.username_input)
        self.main_layout.add_widget(self.password_input)
        self.main_layout.add_widget(self.command_input)
        self.main_layout.add_widget(self.blockchain_name_input)

        self.register_button = Button(text='Register')
        self.register_button.bind(on_press=self.register_user)
        self.main_layout.add_widget(self.register_button)

        self.login_button = Button(text='Login')
        self.login_button.bind(on_press=self.login_user)
        self.main_layout.add_widget(self.login_button)

        self.search_button = Button(text='Search')
        self.search_button.bind(on_press=self.search_files)
        self.main_layout.add_widget(self.search_button)

        self.backup_button = Button(text='Backup')
        self.backup_button.bind(on_press=self.backup_files)
        self.main_layout.add_widget(self.backup_button)

        self.get_file_button = Button(text='Get File')
        self.get_file_button.bind(on_press=self.get_file)
        self.main_layout.add_widget(self.get_file_button)

        self.grant_permission_button = Button(text='Grant Permission')
        self.grant_permission_button.bind(on_press=self.grant_permission)
        self.main_layout.add_widget(self.grant_permission_button)

        self.get_all_button = Button(text='Get All Files')
        self.get_all_button.bind(on_press=self.get_all_files)
        self.main_layout.add_widget(self.get_all_button)

        self.load_blockchain_button = Button(text='Load Blockchain')
        self.load_blockchain_button.bind(on_press=self.load_blockchain)
        self.main_layout.add_widget(self.load_blockchain_button)

        self.check_integrity_button = Button(text='Check Blockchain Integrity')
        self.check_integrity_button.bind(on_press=self.check_integrity)
        self.main_layout.add_widget(self.check_integrity_button)

        return self.main_layout

    def register_user(self, instance):
        blockchain_name = self.blockchain_name_input.text.strip()
        if not blockchain_name:
            self.show_popup("Error", "Blockchain name must be provided.")
            return
        if not hasattr(self, 'file_blockchain'):
            self.initialize_blockchains(blockchain_name)

        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        if not username or not password:
            self.show_popup("Error", "Username and password cannot be empty.")
            return
        if self.file_blockchain.register_user(username, password):
            self.show_popup("Success", f"User {username} registered successfully.")
        else:
            self.show_popup("Error", f"User {username} already exists.")

    def login_user(self, instance):
        blockchain_name = self.blockchain_name_input.text.strip()
        if not blockchain_name:
            self.show_popup("Error", "Blockchain name must be provided.")
            return
        if not hasattr(self, 'file_blockchain'):
            self.initialize_blockchains(blockchain_name)

        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        if not username or not password:
            self.show_popup("Error", "Username and password cannot be empty.")
            return
        if self.file_blockchain.authenticate_user(username, password):
            self.current_user[0] = username
            self.show_popup("Success", f"User {username} logged in successfully.")
        else:
            self.show_popup("Error", "Invalid username or password.")

    def initialize_blockchains(self, blockchain_name):
        self.file_blockchain = FileBlockchain(blockchain_name=blockchain_name)
        self.access_blockchain = AccessBlockchain(blockchain_name=blockchain_name)
        self.index_blockchain = IndexBlockchain(blockchain_name=blockchain_name)

    def search_files(self, instance):
        if self.current_user[0]:
            search_word = self.command_input.text
            search_results = self.file_blockchain.search_files(search_word)
            results = "\n".join([f"File Name: {result['file_name']}, Owner: {result['owner']}, Date: {result['file_date']}" for result in search_results])
            self.show_popup(f"Search results for '{search_word}':", results)
        else:
            self.show_popup("Error", "Please log in to search files.")

    def backup_files(self, instance):
        if self.current_user[0]:
            blockchain_name = self.blockchain_name_input.text.strip()
            if not blockchain_name:
                self.show_popup("Error", "Backup name cannot be empty.")
                return

            self.file_blockchain.blockchain_name = blockchain_name
            self.access_blockchain.blockchain_name = blockchain_name
            self.index_blockchain.blockchain_name = blockchain_name

            directory_to_add = '.'  # Specify the directory with files to add
            print(f"Starting backup process for blockchain: {blockchain_name}")

            for root, _, files in os.walk(directory_to_add):
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self.file_blockchain.is_file_in_chain(file_path):
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

                        print(f"Adding file {file_path} to blockchain.")
                        try:
                            self.file_blockchain.add_file(file_path, file_date, content, self.current_user[0],
                                                          self.access_blockchain,
                                                          self.index_blockchain)

                            # Check integrity after each block is added
                            if not self.file_blockchain.verify_chain_integrity():
                                print(f"Integrity check failed after adding file {file_path}. Aborting backup.")
                                self.show_popup("Error",
                                                f"Integrity check failed after adding file {file_path}. Aborting backup.")
                                return
                        except ValueError as e:
                            print(f"Error while adding file {file_path}: {e}")
                            self.show_popup("Error", f"Error while adding file {file_path}: {e}")
                            return

            print("Updating file index and reloading chain...")
            self.file_blockchain.update_file_index()
            self.file_blockchain.load_chain()

            print("Verifying blockchain integrity after backup...")
            if self.file_blockchain.verify_chain_integrity():
                print(f"Backup of {blockchain_name} blockchain completed successfully.")
                self.show_popup("Success", f"Backup of {blockchain_name} blockchain completed.")
            else:
                print(f"Backup of {blockchain_name} blockchain completed but integrity check failed.")
                self.show_popup("Error",
                                f"Backup of {blockchain_name} blockchain completed but integrity check failed.")
        else:
            self.show_popup("Error", "Please log in to backup files.")

    def get_file(self, instance):
        if self.current_user[0]:
            parts = self.command_input.text.split()
            if len(parts) != 2:
                self.show_popup("Error", "Enter a file name and an output name.")
                return
            file_name = parts[0]
            output_name = parts[1]
            if self.file_blockchain.is_file_in_chain(file_name):
                if self.access_blockchain.has_access(file_name, self.current_user[0]):
                    content = self.file_blockchain.get_file_content(file_name, self.file_blockchain.users[self.current_user[0]],
                                                               is_shared=True)
                    if content:
                        with open(output_name, 'wb') as output_file:
                            output_file.write(content)
                        self.show_popup("Success", f'Content of {file_name} saved to {output_name}')
                    else:
                        self.show_popup("Error", f'User {self.current_user[0]} does not have access to {file_name}')
                else:
                    self.show_popup("Error", f'File {file_name} access not granted')
            else:
                self.show_popup("Error", 'File does not exist in the blockchain')
        else:
            self.show_popup("Error", "Please log in to get files.")

    def grant_permission(self, instance):
        if self.current_user[0]:
            parts = self.command_input.text.split()
            if len(parts) != 2:
                self.show_popup("Error", "Enter a file path and a user to grant permission to.")
                return
            path_to_grant = parts[0]
            user_to_grant = parts[1]
            if os.path.isdir(path_to_grant):
                for root, _, files in os.walk(path_to_grant):
                    for file in files:
                        relative_file_path = os.path.relpath(os.path.join(str(root), file), start=os.getcwd())
                        if self.file_blockchain.is_file_in_chain(relative_file_path):
                            self.access_blockchain.grant_access(relative_file_path, self.current_user[0], user_to_grant)
                            self.access_blockchain.save_access_chain()
                            self.show_popup("Success", f"Access to {relative_file_path} granted to {user_to_grant}")
                        else:
                            self.show_popup("Error", f"File {relative_file_path} does not exist in the blockchain")
            else:
                if self.file_blockchain.is_file_in_chain(path_to_grant):
                    self.access_blockchain.grant_access(path_to_grant, self.current_user[0], user_to_grant)
                    self.access_blockchain.save_access_chain()
                    self.show_popup("Success", f"Access to {path_to_grant} granted to {user_to_grant}")
                else:
                    self.show_popup("Error", "File does not exist in the blockchain")
        else:
            self.show_popup("Error", "Please log in to grant permission.")

    def get_all_files(self, instance):
        if self.current_user[0]:
            self.file_blockchain.load_chain()
            output_dir = 'extracted'
            os.makedirs(output_dir, exist_ok=True)
            file_list = self.file_blockchain.get_file_list()
            for file in file_list:
                file_name = file['file_name']
                if self.access_blockchain.has_access(file_name, self.current_user[0]):
                    content = self.file_blockchain.get_file_content(file_name, self.current_user[0])
                    if content:
                        output_path = os.path.join(output_dir, file_name)
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'wb') as output_file:
                            output_file.write(content)
                        print(f'Extracted {file_name} to {output_path}')
                    else:
                        self.show_popup("Error", f'User {self.current_user[0]} does not have access to {file_name}')
                else:
                    self.show_popup("Error", f'File {file_name} access not granted')
        else:
            self.show_popup("Error", "Please log in to get all files.")

    def load_blockchain(self, instance):
        blockchain_name = self.blockchain_name_input.text.strip()
        if not blockchain_name:
            self.show_popup("Error", "Blockchain name cannot be empty.")
            return

        backup_dir = 'file_blockchain' # Directory where backup blocks are stored
        self.file_blockchain.blockchain_name = blockchain_name
        self.access_blockchain.blockchain_name = blockchain_name
        self.index_blockchain.blockchain_name = blockchain_name

        block_files = sorted([f for f in os.listdir(backup_dir) if f.startswith(f'{blockchain_name}_block_')])
        for block_file in block_files:
            block_path = os.path.join(backup_dir, block_file)
            with open(block_path, 'rb') as file:
                block = pickle.load(file)
                self.file_blockchain.chain.append(block)
                self.file_blockchain.chunk_index[block.index] = block_path

        self.file_blockchain.update_file_index()
        self.file_blockchain.load_chain()
        self.show_popup("Success", f"Loaded backup from {blockchain_name} into blockchain.")

    def check_integrity(self, instance):
        print("Checking blockchain integrity...")
        for i, block in enumerate(self.file_blockchain.chain):
            if i > 0:  # Skip the genesis block
                prev_block = self.file_blockchain.chain[i - 1]
                if block.prev_hash != prev_block.calculate_hash:
                    print(f"Block {block.index} has invalid previous hash.")
                    self.show_popup("Error", f"Block {block.index} has invalid previous hash.")
                    return
                if not self.file_blockchain.check_validity(block, prev_block):
                    print(f"Block {block.index} is invalid.")
                    self.show_popup("Error", f"Block {block.index} is invalid.")
                    return
        print("Blockchain integrity verified.")
        self.show_popup("Success", "Blockchain integrity verified.")

    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation='vertical')
        popup_label = Label(text=message)
        close_button = Button(text='Close')
        popup_layout.add_widget(popup_label)
        popup_layout.add_widget(close_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, 0.5))
        close_button.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    BlockchainApp().run()
