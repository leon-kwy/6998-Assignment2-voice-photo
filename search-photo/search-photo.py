import json
import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
# this is the test
region = 'us-east-1'
service = 'es'
s3 = boto3.client('s3')
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)


def lambda_handler(event, context):
    query_sentence = event["queryStringParameters"]['q']

    keywords = lex_getkey(query_sentence)
    # print(keywords)
    urls = photos_search(keywords)

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            # "Access-Control-Allow-Credentials":True,
            "Content-Type": "application/json"
        },
        "body": json.dumps(urls),
    }


#     {
#     "statusCode": 200,
#     "headers": {
#         "Access-Control-Allow-Origin": "*",
#         "Content-Type": "application/json"
#     },
#     "body": "{\"results\": [\"https://bucketforas2.s3.amazonaws.com/testImage04.jpg\"]}"
# }


def lex_getkey(query_sentence):
    # Pick up key words using Lex
    client = boto3.client('lex-runtime')
    response = client.post_text(
        botName='VoiceControlledPhotoAlbum',
        botAlias='photo',
        userId='nobody',
        inputText=query_sentence,
    )

    print(response['slots'])
    slots = response['slots']
    key_words = [i for _, i in slots.items() if i]
    keywords = key_words[0].split(" ")

    return keywords


def photos_search(keywords):
    host = 'vpc-photos-adcvyio52sjj2qm4zxtslr5lty.us-east-1.es.amazonaws.com'

    es = Elasticsearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    urls = []

    for k in keywords:
        q = {
            'query': {
                'match': {
                    'labels': k
                }
            }
        }
        print(k)

        query_info = json.dumps(q)
        print(query_info)
        res = es.search(index="photoinfo", body=query_info)
        # response = res.json()
        # print(res)
        print("Got %d Hits:" % res['hits']['total']['value'])
        for hit in res['hits']['hits']:
            bucket = hit['_source']['bucket']
            objectKey = hit['_source']['objectKey']
            photo_url = 'https://' + bucket + '.s3.amazonaws.com/' + objectKey

            if photo_url not in urls:
                urls.append(photo_url)
    return urls
