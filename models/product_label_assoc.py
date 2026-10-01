from extensions import db

from models.label import Label      

product_labels = db.Table(
    'product_labels_assoc',
    db.Column('id', db.Integer, primary_key=True, autoincrement=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False),
    db.Column('label_id', db.Integer, db.ForeignKey('label.id', ondelete='CASCADE'), nullable=False),
    db.Index('idx_product_label', 'product_id', 'label_id', unique=True),
    mysql_engine='InnoDB',
    mysql_auto_increment='1'
)