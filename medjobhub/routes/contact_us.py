from medjobhub import request, jsonify,Mail,Message,app
mail=Mail(app)


#Sending Response Email for Contact Message
def send_contact_response_email(recipient_email, username):
    with app.app_context():
        msg = Message(
            'Thank You for Contacting MedJobHub!',
            sender="MedJobHub <medjobhub>",
            recipients=[recipient_email]
        )
        msg.body = f"""
Hello {username},

Thank you for reaching out to us! We have received your message and will get back to you as soon as possible. 
Our team is reviewing your inquiry, and we appreciate your patience.

If your request is urgent, feel free to reply to this email or contact us directly.

Best regards,  
The MedJobHub Team  
"""
        try:
            mail.send(msg)
            print("Response email sent successfully!")
            return True
        except Exception as e:
            print(f"Error sending response email: {e}")
            return False


#Contact_US
@app.route('/contact_us', methods=['POST'])
def contact_us():
    try:
        data = request.json  
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        message = data.get('message')

        if not name or not email or not message:
            return jsonify({"success":False,"message": "Name, Email, and Message are required!"})

        send_contact_response_email(email, name)

        return jsonify({"success":True,"message": "Thank you for contacting us! We will get back to you soon."})

    except Exception as e:
        print(f"Error processing contact request: {e}")
        return jsonify({"success":False,"message": "Something went wrong. Please try again later."})
