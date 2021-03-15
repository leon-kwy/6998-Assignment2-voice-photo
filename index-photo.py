import json
import boto3
import requests
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from datetime import date, datetime

region = 'us-east-1'
service = 'es'
s3 = boto3.client('s3')
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
host = 'vpc-photos-adcvyio52sjj2qm4zxtslr5lty.us-east-1.es.amazonaws.com'


# url = host + '/' + index + '/' + type
# url_novpc = host_novpc + '/' + index + '/' + type
# headers = {"Content-Type": "application/json"}


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


def get_labels(bucket, photo_name, customlabel):
    client = boto3.client('rekognition')

    print("photo_name", photo_name)
    print("bucket", bucket)

    response = client.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': photo_name
            }
        },
        MaxLabels=8
    )

    # print("response",response)

    labels = []
    for label_name in response['Labels']:
        labels.append(label_name['Name'].lower())

    customlabel2 = customlabel.split(",")
    for i in customlabel2:
        labels.append(i)

    print("final labels", labels)
    return labels


def lambda_handler(event, context):
    # Get the bucket name and photo name

    print("event", event)

    bucket = event['Records'][0]['s3']['bucket']['name']
    photo_name = event['Records'][0]['s3']['object']['key']
    print(bucket)
    print(photo_name)

    try:
        response = s3.head_object(Bucket=bucket, Key=photo_name)
        print("response", response['Metadata'])
        customlabel = response['Metadata']['customlabels']
    except:
        print("no custom label")

    # Get the labels
    labels = get_labels(bucket, photo_name, customlabel)

    # Get the timestamp of Image
    response = s3.head_object(
        Bucket=bucket,
        Key=photo_name
    )
    datetime_value = response["LastModified"]
    # print(datetime_value)

    # JSON message stored in ES
    message = {
        'objectKey': photo_name,
        'bucket': bucket,
        'createdTimestamp': datetime_value,
        'labels': labels
    }

    message = json.dumps(message, indent=4, cls=ComplexEncoder)
    print(message)

    # Upload the message
    es = Elasticsearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    res = es.index(index="photoinfo", doc_type="_doc", body=message)
    print(res['result'])

    # res = es.get(index="photoinfo", id=2)
    # print(res['_source'])


if __name__ == "__main__":
    lambda_handler(None, None)




















