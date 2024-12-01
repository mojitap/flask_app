{\rtf1\ansi\ansicpg932\cocoartf2709
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;\f1\fnil\fcharset128 HiraginoSans-W3;\f2\fnil\fcharset0 HelveticaNeue;
}
{\colortbl;\red255\green255\blue255;\red13\green16\blue19;}
{\*\expandedcolortbl;;\cssrgb\c5882\c7843\c9804;}
\paperw11900\paperh16840\margl1440\margr1440\vieww10800\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import tweepy\
\
# 
\f1 \'82\'b1\'82\'b1\'82\'c9\'8e\'e6\'93\'be\'82\'b5\'82\'bd
\f0 API
\f1 \'83\'4c\'81\'5b\'82\'c6\'83\'41\'83\'4e\'83\'5a\'83\'58\'83\'67\'81\'5b\'83\'4e\'83\'93\'82\'f0\'93\'fc\'97\'cd
\f0 \
api_key = '
\f2\fs30 \cf2 \expnd0\expndtw0\kerning0
Tgrh1s8o4hS1OwERLi0STxd0t
\f0\fs24 \cf0 \kerning1\expnd0\expndtw0 '\
api_key_secret = '
\f2\fs30 \cf2 \expnd0\expndtw0\kerning0
1BOzIzTXYxo9cV2GhR6OgChYrQm9tkm1dm1TgShicPAv1bEvSf
\f0\fs24 \cf0 \kerning1\expnd0\expndtw0 '\
access_token = '
\f2\fs30 \cf2 \expnd0\expndtw0\kerning0
1553182578466701312-QOgsFeHe4khiMn9t2g4oTT4GsTPUmx
\f0\fs24 \cf0 \kerning1\expnd0\expndtw0 '\
access_token_secret = '
\f2\fs30 \cf2 \expnd0\expndtw0\kerning0
WZzDOGIIw4Hk1cLIeRGO1MJs2aNUYM12SRoRZVsOpiVqJ
\f0\fs24 \cf0 \kerning1\expnd0\expndtw0 '\
\
# Twitter API
\f1 \'82\'d6\'82\'cc\'94\'46\'8f\'d8
\f0 \
auth = tweepy.OAuthHandler(api_key, api_key_secret)\
auth.set_access_token(access_token, access_token_secret)\
\
# API
\f1 \'83\'49\'83\'75\'83\'57\'83\'46\'83\'4e\'83\'67\'82\'f0\'8d\'ec\'90\'ac
\f0 \
api = tweepy.API(auth)\
\
# 
\f1 \'8c\'9f\'8d\'f5\'82\'b7\'82\'e9\'83\'4c\'81\'5b\'83\'8f\'81\'5b\'83\'68\'82\'c6\'83\'63\'83\'43\'81\'5b\'83\'67\'90\'94\'82\'f0\'8e\'77\'92\'e8
\f0 \
keyword = "
\f1 \'96\'bc\'97\'5f\'9a\'ca\'91\'b9
\f0  OR 
\f1 \'94\'ee\'e6\'8e\'92\'86\'8f\'9d
\f0 "\
tweets = api.search_tweets(q=keyword, lang="ja", count=10)\
\
# 
\f1 \'8c\'9f\'8d\'f5\'8c\'8b\'89\'ca\'82\'f0\'95\'5c\'8e\'a6
\f0 \
for tweet in tweets:\
    print(f"\{tweet.user.name\}: \{tweet.text\}")\
\
\
\
}