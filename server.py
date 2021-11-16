from os import stat
from flask import Flask, request, render_template
from flask.wrappers import Response
import requests
from logging import FileHandler, WARNING, debug, error, exception
from datetime import datetime, date, time
import json
import calendar
import time

# Monday.com API key authentication
apiKey = "Your monday.com API key here"
apiUrl = "https://api.monday.com/v2"
headers = {"Authorization" : apiKey}

app = Flask(__name__)


# Error Log
if not app.debug:
    file_handler = FileHandler('errorlog.txt')
    file_handler.setLevel(WARNING)

    app.logger.addHandler(file_handler)


# Function to retrieve item_id using order_id
def get_item_id(order_id):

    order_id = str(order_id)
    query = """ query($value: String!) {
                        items_by_column_values(
                            board_id: 1899225171,
                             column_id: "text3", 
                             column_value: $value) {
                        id
                         }
                        }"""

    vars ={
        'value' : order_id,
            
    }
       
    data ={'query':query, 'variables' : vars}

    # Returns error page if order does not exist
    # Captures IndexError
    try:
        r = requests.post(url=apiUrl, json=data, headers=headers)
        response = r.json()
        print(response)
        item_id = response['data']['items_by_column_values'][0]['id']
        
    except Exception as e:
        return -1

    return int(item_id)


# Function to find the status of the order
def order_status(item_id):
    query2 = """ query ($item_id: Int!){
                        boards(ids:1899225171){
                            items(ids:[$item_id]){
                                id
                                name
                                column_values(ids:["status0"]){
                                    
                                    title
                                    value
                                }

                                
                               
                            }
                        }
        }
        """
    vars ={
        'item_id' : item_id,
                
    }
                
       
    data ={'query':query2,'variables' : vars}
    r = requests.post(url=apiUrl, json=data, headers=headers)
    response = r.json()
        
    status = response['data']['boards'][0]['items'][0]['column_values'][0]['value'][9]
    return status


#  ROUTES

# Index page
@app.route("/")
def display_home():
    return "Welcome"

# For creating new order
@app.route("/order", methods=['POST'])
def create_order():

    if request.method == 'POST':
        color = request.form['color']
        size = request.form['size']
        message = request.form['message']
        item_name = request.form['item']
        quantity = request.form['quantity']
        
        # Today's date in JSON format
        today = datetime.now().date()
        today = today.isoformat()

        # Timestamp to create unique Order_ID
        gmt = time.gmtime()
        order_id = str(calendar.timegm(gmt))

        
        # Graphql query for creating new item with column values populated
        query = """mutation ($myItemName: String!, $columnVals: JSON!)
                     { 
                        create_item (
                            board_id:1899225171, 
                            item_name:$myItemName, 
                            column_values:$columnVals) 
                            { 
                                id 
                            } 
                    }"""
        vars = {
            'myItemName' : item_name,
            'columnVals' : json.dumps({
            'status0': {'label' : "Working on it"},
            'date4' : {'date' : today},
            'text': color,
            'text7': message,
            'dropdown': {'labels' : [size]},
            'numbers': quantity,
            'text3': order_id
            })
            }
        
        # Calling Monday.com API
        data ={'query':query, 'variables' : vars}
        r = requests.post(url=apiUrl, json=data, headers=headers)
        
        # Details of the created item returned to the browser
        return r.json()
        


# Route for modifying an existing order
@app.route("/modify/<int:order_id>", methods=['PUT'])
def modify(order_id):

    if request.method == 'PUT':
        color = request.form['color']
        size = request.form['size']
        message = request.form['message']
        quantity = request.form['quantity']
        
       
        #  Today's date in JSON format
        today = datetime.now().date()
        today = today.isoformat()
        
        # Calls function to obtain item_id
        item_id = get_item_id(order_id) 

        # Returns error page if order ID does not exist
        if item_id == -1:
            return render_template("error_handling.html")
        

        #  Checks if the order has already been processed. Returns regret message, if so.
        status = order_status(item_id)
        if status == "1":
            return({
                'message':"Sorry! Order processed already! Cannot be modified now."
            })  
        
        # Query for Modifying the order details in 'monday.com' 
        query = """mutation ($item_id: Int!, $columnVals: JSON!)
                     { 
                        change_multiple_column_values (
                            board_id:1899225171, 
                            item_id:$item_id, 
                            column_values:$columnVals) 
                            { 
                                id 
                            } 
                    }"""
        vars = {
            'item_id' : item_id,
            'columnVals' : json.dumps({
            'status0': {'label' : "Working on it"},
            'date4' : {'date' : today},
            'text': color,
            'text7': message,
            'dropdown': {'labels' : [size]},
            'numbers': quantity,
            'text3': str(order_id)
            })
            }
        
        # Calling Monday.com API
        data ={'query':query, 'variables' : vars}
        r = requests.post(url=apiUrl, json=data, headers=headers)

        # Details of the modified item passed to the browser
        return r.json()


# Route for deleting a particular order
@app.route("/delete/<int:order_id>", methods=['DELETE'])
def delete(order_id):

    if request.method == 'DELETE':
        
        
        # Calling function to retrieve item_id
        item_id = get_item_id(order_id)
        
        # Returns error page if order ID does not exist
        if item_id == -1:
            return render_template("error_handling.html")
              

        #  Checks if the order has already been processed. Returns regret message, if so.
        status = order_status(item_id)
        if status == "1":
            return({
                'message':"Sorry! Order processed already! Cannot be deleted now."
            })


        # Query for deleting order details from 'monday.com'
        query = """mutation($item_id: Int!) {
                    delete_item(
                            
                            item_id:$item_id)
                            {
                                id
                            }                            
                            
                    }"""
        vars = {
            'item_id': item_id
        }
        
        # Calling Monday.com API      
        data ={'query':query,'variables' : vars}
        r = requests.post(url=apiUrl, json=data, headers=headers)
        
        # Details of the deleted item passed to the browser
        return r.json()
        

# Route for displaying order status 
@app.route("/order_details/<int:order_id>", methods=['GET'])
def order_details(order_id):
       
    # order_id = request.form['order_id']
       
    # Calling function to retrieve item_id
    item_id = get_item_id(order_id)
    
    # Returns error page if order ID does not exist
    if item_id == -1:
        return render_template("error_handling.html")
    
       

    # Calls the function that returns the status    
    status = order_status(item_id)
        
    # Displays the message as per status received
    progress ={
            '0': "Working on it",
            '1': "Done",
            '2': "Stuck"
        }

    # Status passed to the browser
    return progress[status]
        

if __name__=="__main__":
    app.run(debug=True)