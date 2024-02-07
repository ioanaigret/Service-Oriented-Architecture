import pika

def process_message(message):
    return message.upper()

def callback(ch, method, properties, body):
    message = body.decode()
    
    processed_message = process_message(message)
    
    print("Received message:", message)
    print("Processed message:", processed_message)


connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', pika.PlainCredentials('user', 'password')))
channel = connection.channel()
channel.queue_declare(queue='book_queue')
channel.basic_consume(queue='book_queue', on_message_callback=callback, auto_ack=True)
print('Waiting for messages. To exit, press CTRL+C')
channel.start_consuming()
