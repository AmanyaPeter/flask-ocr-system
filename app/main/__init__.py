from flask import Blueprint

# 1. Create the Blueprint for the 'main' section of the app.
#    - 'main' is the name of the blueprint.
#    - __name__ tells the blueprint where it's defined.
#    - template_folder specifies that this blueprint will look for its
#      templates in a specific sub-folder. This is great for organization.
main_bp = Blueprint(
    'main',
    __name__,
    template_folder='../templates/main'
)

# 2. Import the routes at the bottom.
#    This is crucial to connect the routes defined in routes.py
#    to the blueprint we just created. It avoids circular import errors.
from . import routes
