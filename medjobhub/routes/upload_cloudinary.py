import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)


# To Upload photos into cloudinary and get url

# @app.route('/upload_image_to_cloudinary', methods=['GET'])
# def upload_image_to_cloudinary(file_name):
#     # Define the path to the image in your static folder
#     image_path = f"backend\medjobhub\static\images\{file_name}"  # Replace with your image name
    
#     try:
#         # Upload image to Cloudinary
#         response = cloudinary.uploader.upload(image_path)
        
#         # Get the Cloudinary URL of the uploaded image
#         image_url = response['secure_url']
        
#         # Return the image URL as a response
#         print("Image uploaded successfully for file ",file_name," and url is: ",image_url)
#     except Exception as e:
#         print("Error occured: ",e)


#To upload files from input
def upload_files_to_cloudinary(file_name):
    try:
        response = cloudinary.uploader.upload(file_name,resource_type="raw")
        
        file_url = response['secure_url']
        print("File uploaded successfully for ", file_name, "and url is:", file_url)
        return file_url  
    except Exception as e:
        print("Error occurred:", e)
        return None  

