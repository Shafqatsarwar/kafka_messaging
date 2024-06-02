from sqlmodel import Session, select
from app.models.product_model import Product
from fastapi import HTTPException

# Add a New Product to the Database
def add_new_product(product_data: Product, session: Session):
    print("Adding Product to Database")
    session.add(product_data)
    session.commit()
    session.refresh(product_data)
    return product_data

# Get All Products from the Database
def get_all_products(session: Session):
    all_products = session.exec(select(Product)).all()
    return all_products

    # Get a product by Id
def get_product_by_id(product_id:int, session=Session):
    product= session.exec(select(Product).where(Product.id= product_id)).one_or_none
    if product is None:
         raise HTTPException(status_code=404, details="Productnot found")
    return product

    # Update a product by Id
def update_product_by_id(product_id: int, to_update_product_data, session=Session):
    product= session.exec(select(Product).where(Product.id= product_id)).one_or_none
    if product is None:
        raise HTTPException(status_code=404, details = "Product not Found")
    # step 2
    product.sqlmodel_update(to_update_product_data)
    session.add(product)
    session.commit()
    return product
    pass

    # Delete a product by Id
def delete_product_by_id(product_id: int, session=Session):
    # step 1
    product= session.exec(select(Product).where(Product.id= product_id)).one_or_none
    if product is None:
        raise HTTPException(status_code=404, details = "Product not Found")
    # step 2
    session.delete(product)
    session.commit()
    return {"message": "Product deleted succesfully"}