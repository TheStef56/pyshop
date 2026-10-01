from extensions import db

# Create association table directly
product_categories = db.Table(
    'product_categories_assoc',
    db.Column('id', db.Integer, primary_key=True, autoincrement=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False),
    db.Column('category_id', db.Integer, nullable=False),
    db.Index('idx_product_category', 'product_id', 'category_id', unique=True),
    mysql_engine='InnoDB',
    mysql_auto_increment='1'
)
