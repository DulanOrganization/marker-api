import pika

parameters = pika.ConnectionParameters(host='35.202.12.228', port=5672, 
                                       credentials=pika.PlainCredentials('guest', 'guest'))
try:
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    print("RabbitMQ is up and reachable!")
    connection.close()
except Exception as e:
    print("Failed to connect to RabbitMQ:", e)