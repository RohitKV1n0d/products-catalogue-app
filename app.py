from flask import Flask, request, jsonify, render_template, url_for ,redirect, session, make_response, flash
#sql
from flask_sqlalchemy import SQLAlchemy

import xlrd
import os


app = Flask(__name__)

ENV = 'prod'

if ENV == 'prod' :
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
    app.config['SECRET_KEY'] = 'asdasdasdasdasdasdasdaveqvq34c'

else:
    app.debug = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SECRET_KEY'] = SECRET_KEY
    
SQLALCHEMY_TRACK_MODIFICATIONS = False

db = SQLAlchemy(app)


class Products(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(50), unique=True)
    item_name = db.Column(db.String(50))
    category_l1 = db.Column(db.String(50))
    category_l2 = db.Column(db.String(50))
    upc = db.Column(db.String(50))
    parent_code = db.Column(db.String(50), db.ForeignKey('products.item_code'))
    mrp_price = db.Column(db.Float)
    size = db.Column(db.String(10))
    enabled = db.Column(db.Boolean)

    children = db.relationship('Products', backref=db.backref('parent', remote_side=[item_code]))
    
    def __repr__(self):
        return f'<Products {self.item_code}>'
    

@app.route('/')
def index():
    products = Products.query.all()
    return render_template('index.html', products=products)



#upload file xlrd 
@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            return 'No file found'
        else:
            xl_workbook = xlrd.open_workbook(file_contents=file.read())
            xl_sheet = xl_workbook.sheet_by_index(0)
            num_rows = xl_sheet.nrows
            for row in range(1, num_rows):
                item_code = xl_sheet.cell(row, 0).value
                item_name = xl_sheet.cell(row, 1).value
                category_l1 = xl_sheet.cell(row, 2).value
                category_l2 = xl_sheet.cell(row, 3).value
                upc = xl_sheet.cell(row, 4).value
                parent_code = xl_sheet.cell(row, 5).value
                mrp_price = xl_sheet.cell(row, 6).value
                size = xl_sheet.cell(row, 7).value
                enabled = xl_sheet.cell(row, 8).value
                if enabled == 'Y' or enabled == 'Yes':
                    enabled = True
                else:
                    enabled = False
                if parent_code == '':
                    parent_code = None
                product = Products(item_code=item_code, item_name=item_name, category_l1=category_l1, category_l2=category_l2, upc=upc, parent_code=parent_code, mrp_price=mrp_price, size=size, enabled=enabled)
                db.session.add(product)
                db.session.commit()
            return redirect(url_for('index'))
        
@app.route('/parent/<string:item_code>', methods=['GET'])
def get_top_parent(item_code):
    product = Products.query.filter_by(item_code=item_code).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    top_parent = product
    while top_parent.parent:
        top_parent = top_parent.parent
    return jsonify({'top_parent': top_parent.item_name}), 200


@app.route('/children/<string:item_name>', methods=['GET'])
def get_children(item_name):
    product = Products.query.filter_by(item_name=item_name).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    children_names = [child.item_name for child in sorted(product.children, key=lambda x: x.item_name)]
    return jsonify({'children': children_names}), 200

@app.route('/active-inactive-count', methods=['GET'])
def get_active_inactive_count():
    active_count = Products.query.filter_by(enabled=True).count()
    inactive_count = Products.query.filter_by(enabled=False).count()
    return jsonify({'active_count': active_count, 'inactive_count': inactive_count}), 200

@app.route('/avg-price-by-category', methods=['GET'])
def get_avg_price_by_category():
    result = {}
    categories_l1 = set([product.category_l1 for product in Products.query.all()])
    categories_l2 = set([product.category_l2 for product in Products.query.all()])
    for category_l1 in categories_l1:
        products_l1 = Products.query.filter_by(category_l1=category_l1).all()
        avg_price_l1 = sum([product.mrp_price for product in products_l1])/len(products_l1)
        result[category_l1] = {}
        result[category_l1]['avg_price'] = avg_price_l1
        for category_l2 in categories_l2:
            products_l2 = Products.query.filter_by(category_l2=category_l2).all()
            avg_price_l2 = sum([product.mrp_price for product in products_l2])/len(products_l2)
            result[category_l1][category_l2] = avg_price_l2
    return jsonify(result), 200


        

#reset database
@app.route('/reset')
def reset():
    db.drop_all()
    db.create_all()
    return render_template('index.html', msg='Database successfully reset')




