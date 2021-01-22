from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    abort,
    url_for
)
from flask_login import (
    UserMixin,
    login_user,
    logout_user,
    current_user,
    LoginManager,
    login_required    
)
from time import time
from uuid import uuid4
from urllib.parse import urlparse
import MySQLdb
import hashlib
import json
import requests
import sys
import config



class BlockChain:




    def __init__(self):
        self.chain = []
        self.current_trx = []
        self.node = set()

        #create the genesis block 
        self.new_block(proof=100, prehash=1)
    

    def Rgister_node(self, addres):
        parsed_url = urlparse(addres)
        self.node.add(parsed_url.netloc)

    def new_block(self, proof, prehash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'trx': self.current_trx,
            'proof': proof,
            'prehash': prehash or self.hash(self.chian[-1]),
        }
    
        #this is for reset the mempool 
        self.current_trx = []
        # we're done with the block so we put it in chain 
        self.chain.append(block)
        return block


    def new_trx(self, sender, reciver, amount):
        self.current_trx.append({
            'sender': sender,
            'reciver': reciver,
            'amount': amount,
        })

        return self.last_block['index'] + 1



    @staticmethod
    def hashkon(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
         

    @property
    def last_block(self):
        return self.chain[-1]


    def proof_of_work(self, last_proof):
        proof = 0 
        while self.valid_proof(last_proof, proof) is False:
            proof += 1 

    @staticmethod
    def valid_proof(last_proof, proof):
        the_proof = f'{last_proof}{proof}'.encode()
        the_proof_hash = hashlib.sha256(the_proof).hexdigest()
        return the_proof_hash[-4:] == '0000'


    def valid_chain(self, chain):
        
        last_block = chain[0]
        current_index = 1 
        while current_index < len(chain):
            block = chain[current_index]
            if block['prehash'] == self.hashkon(last_block):
                return False
            if not valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block 
            current_index += 1
        
        return True 
    
    def concenses(self):
        neibours = self.node
        new_chain = None
        max_length = len(self.chain)

        for node in neibours:
            response = requests.get(f'http://{node}/chain')
             
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

        
            if length < max_length and self.valid_chain(chain):
                new_chain = chain 
                length = max_length

            if new_chain:
                self.chain = new_chain
                return True
        return False



app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

node_id = str(uuid4())

blockchian = BlockChain()



#TODO proofes are null !!!!!!


# @app.route('/')
# def homepage():

#     return flask.render_template


@app.route('/mine')
def mine():
    last_block = blockchian.last_block
    last_proof = last_block['proof']
    proof = blockchian.proof_of_work(last_proof)


    blockchian.new_trx(
        sender=0,
        reciver=node_id,
        amount=50
    )

    previous_hash = blockchian.hashkon(last_block)
    block = blockchian.new_block(proof,previous_hash)


    response = {
        
        'index':block['index'],
        'trx': block['trx'],
        'proof': block['proof'],
        'prehash': block['prehash']
    }


    block_number = block['index']
    proof = block['proof']
    trx = block['trx']
    prehash= block['prehash']
    
    db = get_database_connection()
    cur = db.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS blocks_log(block_number INT(30),proof VARCHAR(400),prehash VARCHAR(400));''')

    cur.execute("INSERT INTO blocks_log(block_number,proof,prehash) VALUES(%s,%s,%s);",(block_number, proof, prehash))
        
    db.commit()
    db.close()

    return jsonify(response), 200



@app.route('/trx/new', methods=['POST'])
def new_trx():
    values = request.get_json()

    required = ['sender','reciver','amount']
    if not all(k in required for k in required):
        return 'Missing Value', 400 

    this_trx=blockchian.new_trx(values['sender'],
                                  values['reciver'],
                                  values['amount'])

    print(type(values['sender']))
    sender = values['sender']
    reciver = values['reciver']
    amount = values['amount']
    
    db = get_database_connection()
    cur = db.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS trx_log(sender char(30),reciver char(30),amount int(30));''')
    cur.execute("INSERT INTO trx_log(sender,reciver,amount) VALUES(%s,%s,%s);",(sender,reciver,amount))
    db.commit()
    db.close()

    response = {'message': f'your new trx will be added to block{new_trx}'}    
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():

    response = {
        'chain': blockchian.chain,
        'length': len(blockchian.chain),

    }
    return jsonify(response), 200


@app.route('/node/register', methods=['POST'])
def node_register():
    values = request.get_json()

    nodes = values.get('node')
    print(nodes)
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400
    for node in nodes:
        print(node)
        blockchian.Rgister_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchian.node),
    }
    return jsonify(response), 201



@app.route('/node/resolve')
def node_resolve():
    replace = blockchian.concenses()

    if replace:
        response = {
            "message": "Chain Changed",
            "New Chain": blockchian.chain
        }
    else:
        response = {
            "message": "our was better",
            "Chain": blockchian.chain
        }

    return jsonify(response), 200

app.config.update(
    DEBUG = True,
    SECRET_KEY = 'secret_xxx'
)

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# silly user model
class User(UserMixin):

    def __init__(self, id):
        self.id = id
        self.name = "user" + str(id)
        self.password = self.name + "_secret"
        
    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)


# create some users with ids 1 to 20       
user = User(0)



# some protected url
@app.route('/')
@login_required
def home():
    return Response("Hello World!")

 
# somewhere to login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']        
        if password == config.PASSWORD and username == config.USERNAME: 
            login_user(user)
            return redirect(request.args.get("next"))
        else:
            return abort(401)
    else:
        return Response('''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
        ''')



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return Response('<p>Logged out</p>')


@app.errorhandler(401)
def page_not_found(e):
    return Response('<p>Login failed</p>')
    
    
@login_manager.user_loader
def load_user(userid):
    return User(userid)

def get_database_connection():
    try:
         """connects to the MySQL database and returns the connection"""
         return MySQLdb.connect(host=config.MYSQL_HOST,
                             user=config.MYSQL_USERNAME,
                            passwd=config.MYSQL_PASSWORD,
                              db=config.MYSQL_DB_NAME,
                             charset='utf8')
    except:
       print('could not connect to db')



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(sys.argv[1]) , debug = True)
