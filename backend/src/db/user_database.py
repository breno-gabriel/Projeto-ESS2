from typing import List, Dict
from uuid import uuid4
from pymongo import MongoClient, errors
from pymongo.collection import Collection, IndexModel
#from src.config.config import env
from logging import INFO, WARNING, getLogger
import datetime
from bcrypt import hashpw, checkpw, gensalt
import hmac
import hashlib
import re
import jsonpickle

logger = getLogger('uvicorn')

cpf_pattern = re.compile(r"^[0-9]{3}\.[0-9]{3}\.[0-9]{3}\-[0-9]{2}$")
cep_pattern = re.compile(r"^[0-9]{5}\-[0-9]{3}$")
email_pattern = re.compile(r"^[\w\.]+@[\w\.]+$")
senha_pattern = re.compile(r"(?=.{8,})(?=.*[0-9].*)(?=.*[a-zA-Z].*)")

class User(object):
    """Classe que representa um usuário do ecommerce

    Returns:
        User, ou None caso o input não seja validado.
    """
    username: str
    nome: str
    sobrenome: str
    cpf: str
    endereço: str | None
    CEP: str | None
    data_de_nascimento: datetime.date
    email: str
    senha: bytes
    id: int
    
    def __new__(cls, username: str, nome: str, sobrenome: str, cpf: str, data_de_nascimento: datetime.date, email: str, senha: str, 
                endereço: str | None = None, CEP: str | None = None):
        if not cpf_pattern.match(cpf):
            return None
        if not (CEP is None) and not (cep_pattern.match(CEP)):
            return None
        if not email_pattern.match(email):
            return None
        if not senha_pattern.match(senha):
            return None

        obj = object.__new__(cls)
        return obj
    
    def __init__(self, username: str, nome: str, sobrenome: str, cpf: str, data_de_nascimento: datetime.date, email: str, senha: str, 
                endereço: str | None = None, CEP: str | None = None): 
        self.username = username
        self.nome = nome
        self.sobrenome = sobrenome
        self.cpf = cpf
        self.endereço = endereço
        self.CEP = CEP
        self.data_de_nascimento = data_de_nascimento
        self.email = email
        self.add_password(senha)
        self.id = abs(hash((datetime.datetime.now(), self.cpf, self.username)))
    
    def add_password(self, senha: str):
        """Atualiza a senha do usuário

        Args:
            senha (str): Senha em formato de string. Não deve ser armazenada em hipótese alguma.
        """
        hash = hmac.new(self.cpf.encode(), senha.encode(), hashlib.sha512)
        self.senha = hashpw(hash.digest(), gensalt())
        
    def check_password(self, senha: str):
        """Verifica se essa senha é a do usuário

        Args:
            senha (str): Senha em formato de string. Não deve ser armazenada em hipótese alguma.

        Returns:
            True se é, ou False se não é
        """
        hash = hmac.new(self.cpf.encode(), senha.encode(),  hashlib.sha512)
        return checkpw(hash.digest(), self.senha)
    

        

class UserDatabase():
    db: dict[User]
    file_path: str
    
    def signup(self, user: User):
        """Alias para add_user"""
        success, reason = self.add_user(user)
        return (success, reason)
    
    
    def __init__(self, path = "Usuários.json"):
        self.db = dict()
        self.file_path = path
        self.try_read_from_file()

    def try_read_from_file(self):
        # Ler users de um arquivo
        import os.path
        if not os.path.exists(self.file_path):
            self.write_to_file()
            return None
        
        with open(self.file_path) as f:
            objetos = f.read()
            db = jsonpickle.decode(objetos)
            if type(db) == dict:
                self.db = db

    def write_to_file(self):
        objetos = jsonpickle.encode(self.db)
        with open(self.file_path, 'w+') as f:
            f.write(objetos)
    
    def add_user(self, user: User, update = True):
        """Adicionar um novo usuário a database

        Args:
            user (User): Usuário em questão
            
        Returns:
            success (bool): True para cadastro bem sucedido, False para mal sucedido
            reason (str): Caso falhe, "CPF" se a razão for um CPF já existente, "USER" se for um user já existente.
            "SUCCESS" caso tenha sido um cadastro bem sucedido
        """
        if update:
            self.try_read_from_file()
        if self.get_user_by_cpf(user.cpf, False):
            return (False, "CPF")
        if self.get_user_by_username(user.nome, False):
            return (False, "USER")
        self.db[user.cpf] = user
        self.write_to_file()
        return (True, "SUCCESS")
    
    def get_user_by_cpf(self, cpf: str, update = True) -> User | None:
        """Pega um usuário da database por cpf. Esse é o método mais eficiente.

        Args:
            cpf (str): Cpf do usuário

        Returns:
            User | None: Usuário retornado
        """
        if update:
            self.try_read_from_file()
        return self.db.get(cpf)
    
    def get_user_by_username(self, username: str, update = True) -> User | None:
        """Pega um usuário da database por username.

        Args:
            username (str): Username do usuário

        Returns:
            User | None: Usuário retornado
        """
        if update:
            self.try_read_from_file()
        for key, val in self.db.items():
            if val.username == username:
                return val
        return None
    
    def get_user_by_id(self, id: int, update = True) -> User | None:
        """Pega um usuário da database por id.

        Args:
            username (str): Id do usuário

        Returns:
            User | None: Usuário retornado
        """
        if update:
            self.try_read_from_file()
        for key, val in self.db.items():
            if val.id == id:
                return val
        return None
        
    def get_user_list(self, update = True) -> list[User]:
        """Retorna a lista de todos os usuários no ecommerce
        """
        if update:
            self.try_read_from_file()
        return list(self.db.values())
    
    def remove_user_by_cpf(self, cpf: str, update = True) -> User | None:
        """Remove o usuário de respectivo CPF

        Args:
            cpf (str): CPF do usuário a ser removido

        Returns:
            User | None: Retorna o User removido, ou None se nenhum foi removido
        """
        if update:
            self.try_read_from_file()
        toreturn = self.db.pop(cpf, None)
        self.write_to_file()
        return toreturn
        