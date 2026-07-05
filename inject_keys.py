import pymongo
client = pymongo.MongoClient('mongodb://logger:logger%40123@ac-ardlond-shard-00-00.own9qdf.mongodb.net:27017,ac-ardlond-shard-00-01.own9qdf.mongodb.net:27017,ac-ardlond-shard-00-02.own9qdf.mongodb.net:27017/tap_sentinel?ssl=true&replicaSet=atlas-1072yl-shard-0&authSource=admin&retryWrites=true&w=majority')
db = client['tap_sentinel']
col = db['licenses']
col.update_one({'key': 'ORAJ-ZXB1-B4ND-5F0I'}, {'$set': {'key': 'ORAJ-ZXB1-B4ND-5F0I', 'status': 'new', 'hwid': 'null', 'licenseType': 'Lifetime'}}, upsert=True)
col.update_one({'key': 'SO24-B4GZ-B2Y8-C60W'}, {'$set': {'key': 'SO24-B4GZ-B2Y8-C60W', 'status': 'new', 'hwid': 'null', 'licenseType': 'Lifetime'}}, upsert=True)
print('Keys injected into MongoDB Atlas!')
