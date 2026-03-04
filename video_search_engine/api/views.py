from django.shortcuts import render, redirect
from django.http import JsonResponse
import json  # Import the json module
from django.http import HttpResponse
from pymongo import MongoClient
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Video, MyUser
from json import JSONEncoder
from django.core.serializers.json import DjangoJSONEncoder
from bson.objectid import ObjectId
from django.views.decorators.http import require_GET, require_POST
from bson import json_util
import hashlib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from .video_graph import Neo4j_Graph
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from datetime import datetime

def frontpage(request):
    return render(request, 'home.html')

def history_view(request):
    return render(request, 'video_info.html')

def like_view(request):
    return render(request, 'like.html')

def playlist_view(request):
    return render(request, 'playlist.html')

def uploaded_video_details(request):
    return render(request, 'upload_video.html')

def generate_id(word):
    return hashlib.md5(word.encode()).hexdigest()

def connect():
    
    connect_string = settings.MONGO_CONNECTION_STRING
    my_client = MongoClient(connect_string)
    # my_client = MongoClient('mongodb://localhost:27017/')
    # First define the database name
    dbname = my_client['Video']

    # Now get/create collection name
    collection_name = dbname["Set_of_videos"]

    return collection_name

def connect_user(): 
    
    connect_string = settings.MONGO_CONNECTION_STRING
    my_client = MongoClient(connect_string)
    # my_client = MongoClient('mongodb://localhost:27017/')
    # First define the database name
    dbname = my_client['Video']

    # Now get/create collection name
    collection_name = dbname["User_History"]

    return collection_name
class MongoEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def serialize_mongo_document(document):
    return json_util.dumps(document)

def store_video(request):
    collection_name = connect()
    collection_name_user = connect_user()

    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    if request.method == 'POST':
        # Get the JSON file from the request.FILES dictionary
        json_file = request.FILES.get('jsonFile', None)

        if json_file:
            try:
                # Parse the JSON content from the file
                json_data = json.loads(json_file.read().decode('utf-8'))
                
                title = json_data['videoInfo']['snippet']['title']
                video_id = json_data['videoInfo']['id']
                likes = int(json_data['videoInfo']['statistics']['likeCount'])
                dislikes = json_data['videoInfo']['statistics']['dislikeCount']
                views = json_data['videoInfo']['statistics']['viewCount']

                user_doc = collection_name_user.find_one({'user.username': user_profile.username})
                # #print(collection_name_user)

                upload_video = user_doc['user']['uploaded_videos']
                upload_video.append(video_id)

                update = {'$set': {'user.uploaded_videos': upload_video}}
                collection_name_user.update_one({'user.username': user_profile.username}, update)

                video = Video(title=title, video_id=video_id, likes=likes, dislikes=dislikes, views=views)
                video.save()

                # Insert the parsed JSON content into the collection
                collection_name.insert_one(json_data)

                return HttpResponse('JSON file uploaded successfully!', status=200)
            except json.JSONDecodeError as e:
                return HttpResponse(f'Error decoding JSON: {str(e)}', status=400)
        else:
            return HttpResponse('No JSON file provided!', status=400)
    
    return render(request, 'channel.html', {'user_profile': user_profile})

@csrf_exempt  # Only for demonstration. Use proper CSRF handling in production.
def update_video_data(request):
    #print(1)
    collection_name = connect()
    collection_name_user = connect_user()
    graph = Neo4j_Graph(collection_name)

    if request.method == 'POST':
        video_id = request.POST.get('video_id', None)
        action = request.POST.get('action', None)
        query = {'videoInfo.id': video_id}
        result = collection_name.find_one({'videoInfo.id': video_id})
        if video_id and action:
            #print(111)
            try:
                #print(444)
                video = Video.objects.get(video_id=video_id)
                if action == 'like':
                    #print(33)
                    video.likes += 1
                    like = int(result['videoInfo']['statistics']['likeCount'])
                    update = {'$set': {'videoInfo.statistics.likeCount': str(like+1)}}
                    collection_name.update_one(query, update)

                    query = {"user.Liked_Videos": {"$in": [video_id]}}

# Execute the query
                    result_check = collection_name_user.find_one(query)
                    # user_history

                    if result_check is None:
                        user_profile = MyUser.objects.get(username=request.user)
                        #print(user_profile.email)

                        user_doc = collection_name_user.find_one({'user.username': user_profile.username})
                        #print(collection_name_user)

                        like = user_doc['user']['Liked_Videos']
                        like.append(video_id)

                        update = {'$set': {'user.Liked_Videos': like}}
                        collection_name_user.update_one({'user.username': user_profile.username}, update)
                    graph.update_node(video_id,"likeCount")
                    #print(video.likes)
                    #print(collection_name.videoInfo.statistics.likeCount)

                elif action == 'dislike':
                    video.dislikes += 1
                    dislike = int(result['videoInfo']['statistics']['dislikeCount'])
                    update = {'$set': {'videoInfo.statistics.dislikeCount': dislike+1}}
                    collection_name.update_one(query, update)

                    query = {"user.Disliked_Videos": {"$in": [video_id]}}

# Execute the query
                    result_check = collection_name_user.find_one(query)
                    # user_history

                    if result_check is None:
                        user_profile = MyUser.objects.get(username=request.user)
                        #print(user_profile.email)

                        user_doc = collection_name_user.find_one({'user.username': user_profile.username})
                        #print(collection_name_user)

                        dislike = user_doc['user']['Disliked_Videos']
                        dislike.append(video_id)

                        update = {'$set': {'user.Disliked_Videos': dislike}}
                        collection_name_user.update_one({'user.username': user_profile.username}, update)

                    graph.update_node(video_id,"dislikeCount")

                video.views += 1  # Increment views for every interaction
                video.save()

                view = int(result['videoInfo']['statistics']['viewCount'])
                update={'$set': {'videoInfo.statistics.viewCount': view+1}}
                collection_name.update_one(query, update)

                return JsonResponse({'success': True})
            except Video.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Video not found'})

    return JsonResponse({'success': False, 'error': 'Invalid request'})

def search_video(request):
    collection_name = connect()

    # if request.user.is_authenticated:
    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)
    if request.method == 'POST':

        # user_profile = MyUser.objects.get(username=request.user)
        # #print(user_profile)

        query = request.POST.get('query', '')
        if query != '':
            result = collection_name.find({
                "$or": [
                    {"videoInfo.snippet.title": {"$regex": f".*{query}.*", "$options": "i"}},
                    {"videoInfo.snippet.description": {"$regex": f".*{query}.*", "$options": "i"}},
                    {"videoInfo.snippet.tags": {"$regex": f".*{query}.*", "$options": "i"}}
                ]
            })
            
            # video_ids = [doc['videoInfo']['id'] for doc in result]
            search_results = [
                {**doc, 'videoInfo': {**doc['videoInfo'], '_id': str(doc['_id'])}} for doc in result
            ]

            # #print(user_profile.name)
            response_data = {
                'query': query,
                'results': search_results,
            }

            # video_information_dict = {}
            # for video in video_ids:
            #     information=Video.objects.get(video_id=video)
            #     video_information_dict[video] = [information.likes, information.dislikes, information.views]

            return JsonResponse(response_data, encoder=MongoEncoder, safe=False)

    return render(request, 'youtube.html', {'user_profile': user_profile})

@require_GET
def get_video_data(request, video_id):
    #print(1)
    collection_name = connect()
    collection_name_user = connect_user()

    result = collection_name.find_one({'videoInfo.id': video_id})
    #print(result)

    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    user_doc = collection_name_user.find_one({'user.username': user_profile.username})
    #print(collection_name_user)

    history = user_doc['user']['History']
    #print(history)
    json_entry = {
        video_id : {
            "date_time": str(datetime.now()),
            "weekday": str(datetime.now().strftime("%A")),
        }
    }
    history.append(json_entry)

    update = {'$set': {'user.History': history}}
    collection_name_user.update_one({'user.username': user_profile.username}, update)

    if result:
        # return JsonResponse(result, encoder=MongoEncoder, safe=False)
        #print(result['videoInfo']['statistics']['likeCount'])
        video_data = {
            'videoInfo': {
                'id': result['videoInfo']['id'],
                'snippet': result['videoInfo']['snippet'],
                'statistics': result['videoInfo']['statistics'],
            }
            # Add more fields as needed
        }
        #print(video_data)

        return JsonResponse({'success': True, 'videoData': video_data})
    else:
        return JsonResponse({'error': 'Video not found'}, status=404)

@csrf_exempt
def upload_video_details(request):
    collection_name = connect()
    collection_name_user = connect_user()

    user_profile = MyUser.objects.get(username=request.user)

    if request.method == 'POST':
        data = json.loads(request.body)
        video_id = data.get('videoId')
        tags = data.get('tags')
        title = data.get('title')
        description = data.get('description')
        
        l=tags.split(',')
           # Create a document

        video = Video(title=title, video_id=video_id, likes=0, dislikes=0, views=0)
        video.save()

        document = {
            "videoInfo": {
                "snippet": {
                "tags": l,
                "channelId": generate_id(user_profile.channel),
                "channelTitle": user_profile.channel,
                "title": title,
                "description": description,
                },
                "kind": "youtube#video",
                "statistics": {
                "commentCount": 0,
                "viewCount": 0,
                "playlistCount": 0,
                "dislikeCount": 0,
                "likeCount": "0"
                },
                "id": video_id
            }
        }

        user_profile = MyUser.objects.get(username=request.user)
        #print(user_profile.email)

        user_doc = collection_name_user.find_one({'user.username': user_profile.username})
        #print(collection_name_user)

        upload_video = user_doc['user']['uploaded_videos']
        upload_video.append(video_id)

        update = {'$set': {'user.uploaded_videos': upload_video}}
        collection_name_user.update_one({'user.username': user_profile.username}, update)
        # Insert the document into the collection
        collection_name.insert_one(document)

        return JsonResponse({'message': 'Data received successfully'})

    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

# @require_GET
# def playlist(request, video_id, action):
#     #print(1)
#     # collection_name = connect()
#     #print(4)
#     collection_name_user = connect_user()
#     #print(3)
#     # Your logic to add/remove the video from playlists based on the action
#     # This function should handle adding/removing a video from playlists based on the video_id and action parameters
#     # result = collection_name.find_one({'videoInfo.id': video_id})
#     query = {"user.playlist": {"$in": [video_id]}}

# # Execute the query
#     result_check = collection_name_user.find_one(query)
#     #print(result_check)

#     if action == 'add' and result_check is None:
#         #print(2)
#         user_profile = MyUser.objects.get(username=request.user)
#         #print(user_profile.email)

#         user_doc = collection_name_user.find_one({'user.username': user_profile.username})
#         #print(collection_name_user)

#         playlist = user_doc['user']['playlist']
#         playlist.append(video_id)

#         update = {'$set': {'user.playlist': playlist}}
#         collection_name_user.update_one({'user.username': user_profile.username}, update)

#     # if result:
#     #     statistics = result.get('videoInfo', {}).get('statistics', {})
#     #     playlist = statistics.get('playlistCount', 0)  # Default value is 0 if not found

#     #     if action == 'add':
#     #         new_playlist_count = playlist + 1
#     #         collection_name.update_one(
#     #             {'videoInfo.id': video_id},
#     #             {'$set': {'videoInfo.statistics.playlistCount': new_playlist_count}}
#     #         )
#             # Perform other operations if needed

#         return JsonResponse({'success': True})
#     else:
#         return JsonResponse({'success': True, 'suggest': 'Video already in playlist'})


def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('login-username')
        password = request.POST.get('login-password')

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect(search_video)
        else:
            messages.info(request, 'Invalid Username or Password')
            return redirect(login_user)

    return render(request, 'login.html')

def createpost(request):
    collection_name = connect_user()

    if request.method == 'POST':
        name = request.POST.get('name')
        email_id = request.POST.get('email')
        user_name = request.POST.get('username')
        password1 = request.POST.get('password')
        password2 = request.POST.get('confirm-password')
        channel_name = request.POST.get('channel_name')
        channel_id = generate_id(channel_name)
        # income = 0
        # deduction = 0

        if password1 != password2:
            messages.info(request, 'Both passwords are not matching')
            return redirect(createpost)
        # Create a new user
        # if password1==password2:
        if MyUser.objects.filter(username=user_name).exists():
            messages.info(request, 'Username is already taken')
            return redirect(createpost)
        elif MyUser.objects.filter(email=email_id).exists():
            messages.info(request, 'Email is already taken')
            return redirect(createpost)
        else:
            new_user = MyUser.objects.create(
                username=user_name,
                email=email_id,
                password=password1,
                name=name,
                channel_id=channel_id,
                channel=channel_name,
                # Total_Income=income,
                # Total_Deduction=deduction
            )
            new_user.set_password(new_user.password)
            new_user.save()

            document = {
                "user": {
                    "username": user_name,
                    "name": name,
                    "channel_id": channel_id,
                    "channel": channel_name,
                    "channel": channel_name,
                    "channel_id": channel_id,
                    "History": [],
                    "Liked_Videos": [],
                    "playlist": [],
                    "uploaded_videos": [],
                }
            }

            # Insert the document into the collection
            collection_name.insert_one(document)
            # return render(request, 'signup.html', {'message': 'User created successfully!'})
            return redirect(login_user)
        # else:
    else:
    # Handle GET request or any other HTTP method
     return render(request, 'signup.html')

@require_GET
def check_like(request, video_id):
    collection_name_user = connect_user()
    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    user_doc = collection_name_user.find_one({'user.username': user_profile.username})
    #print(collection_name_user)

    like = user_doc['user']['Liked_Videos']

    if video_id in like:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})

@require_GET
def check_playlist(request, video_id):
    collection_name_user = connect_user()
    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    user_doc = collection_name_user.find_one({'user.username': user_profile.username})
    #print(collection_name_user)

    playlist = user_doc['user']['playlist']

    if video_id in playlist:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


@require_GET
def get_history(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        history = user_doc['user']['History']
        # #print(history)
        videos = []

        for key in history:
            for k in key.keys():
                #print(k)
                result = collection_name.find_one({'videoInfo.id': k})
                if result:
                    json_video = {
                        "id": k,
                        "title": result['videoInfo']['snippet']['title'],
                        "timing": key[k]['date_time'],
                        "Day": key[k]['weekday']
                    }
                    videos.append(json_video)
        # #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def get_likes(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        liked = user_doc['user']['Liked_Videos']
        #print(liked)
        videos = []

        for key in liked:
            result = collection_name.find_one({'videoInfo.id': key})
            if result:
                json_video = {
                    "id": key,
                    "title": result['videoInfo']['snippet']['title'],
                }
                videos.append(json_video)
        #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def get_playlist(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        playlist = user_doc['user']['playlist']
        #print(playlist)
        videos = []

        for key in playlist:
            result = collection_name.find_one({'videoInfo.id': key})
            if result:
                json_video = {
                    "id": key,
                    "title": result['videoInfo']['snippet']['title'],
                }
                videos.append(json_video)
        #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def get_uploaded_videos(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        upload_video = user_doc['user']['uploaded_videos']
        #print(upload_video)
        videos = []

        for key in upload_video:
            result = collection_name.find_one({'videoInfo.id': key})
            if result:
                json_video = {
                    "id": key,
                    "title": result['videoInfo']['snippet']['title'],
                }
                videos.append(json_video)
        #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def playlist(request, video_id, action):
    #print(1)
    collection_name = connect()
    collection_name_user = connect_user()
    # Your logic to add/remove the video from playlists based on the action
    # This function should handle adding/removing a video from playlists based on the video_id and action parameters
    result = collection_name.find_one({'videoInfo.id': video_id})
    query = {"user.playlist": {"$in": [video_id]}}

# Execute the query
    result_check = collection_name_user.find_one(query)
    #print(result_check)

    if action == 'add' and result_check is None:
        user_profile = MyUser.objects.get(username=request.user)
        #print(user_profile.email)

        user_doc = collection_name_user.find_one({'user.username': user_profile.username})
        #print(collection_name_user)

        playlist = user_doc['user']['playlist']
        playlist.append(video_id)

        update = {'$set': {'user.playlist': playlist}}
        collection_name_user.update_one({'user.username': user_profile.username}, update)

    # if result:
    #     statistics = result.get('videoInfo', {}).get('statistics', {})
    #     playlist = statistics.get('playlistCount', 0)  # Default value is 0 if not found

    #     if action == 'add':
    #         new_playlist_count = playlist + 1
    #         collection_name.update_one(
    #             {'videoInfo.id': video_id},
    #             {'$set': {'videoInfo.statistics.playlistCount': new_playlist_count}}
    #         )
            # Perform other operations if needed

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': True, 'suggest': 'Video already in playlist'})


def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('login-username')
        password = request.POST.get('login-password')

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect(search_video)
        else:
            messages.info(request, 'Invalid Username or Password')
            return redirect(login_user)

    return render(request, 'login.html')

def createpost(request):
    collection_name = connect_user()

    if request.method == 'POST':
        name = request.POST.get('name')
        email_id = request.POST.get('email')
        user_name = request.POST.get('username')
        password1 = request.POST.get('password')
        password2 = request.POST.get('confirm-password')
        channel_name = request.POST.get('channel_name')
        channel_id = generate_id(channel_name)
        # income = 0
        # deduction = 0

        if password1 != password2:
            messages.info(request, 'Both passwords are not matching')
            return redirect(createpost)
        # Create a new user
        # if password1==password2:
        if MyUser.objects.filter(username=user_name).exists():
            messages.info(request, 'Username is already taken')
            return redirect(createpost)
        elif MyUser.objects.filter(email=email_id).exists():
            messages.info(request, 'Email is already taken')
            return redirect(createpost)
        else:
            new_user = MyUser.objects.create(
                username=user_name,
                email=email_id,
                password=password1,
                name=name,
                channel_id=channel_id,
                channel=channel_name,
                # Total_Income=income,
                # Total_Deduction=deduction
            )
            new_user.set_password(new_user.password)
            new_user.save()

            document = {
                "user": {
                    "username": user_name,
                    "name": name,
                    "channel_id": channel_id,
                    "channel": channel_name,
                    "channel": channel_name,
                    "channel_id": channel_id,
                    "History": [],
                    "Liked_Videos": [],
                    "Disliked_Videos": [],
                    "playlist": [],
                    "uploaded_videos": [],
                }
            }

            # Insert the document into the collection
            collection_name.insert_one(document)
            # return render(request, 'signup.html', {'message': 'User created successfully!'})
            return redirect(login_user)
        # else:
    else:
    # Handle GET request or any other HTTP method
     return render(request, 'signup.html')

@require_GET
def check_like(request, video_id):
    collection_name_user = connect_user()
    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    user_doc = collection_name_user.find_one({'user.username': user_profile.username})
    #print(collection_name_user)

    like = user_doc['user']['Liked_Videos']
    dislike = user_doc['user']['Disliked_Videos']

    if video_id in like or video_id in dislike:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


# @require_GET
# def check_dislike(request, video_id):
#     collection_name_user = connect_user()
#     user_profile = MyUser.objects.get(username=request.user)
#     #print(user_profile.email)

#     user_doc = collection_name_user.find_one({'user.username': user_profile.username})
#     #print(collection_name_user)

#     dislike = user_doc['user']['Disliked_Videos']

#     if video_id in dislike:
#         return JsonResponse({'success': True})
#     else:
#         return JsonResponse({'success': False})
    

@require_GET
def check_playlist(request, video_id):
    collection_name_user = connect_user()
    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    user_doc = collection_name_user.find_one({'user.username': user_profile.username})
    #print(collection_name_user)

    playlist = user_doc['user']['playlist']

    if video_id in playlist:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})


@require_GET
def get_history(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        history = user_doc['user']['History']
        # #print(history)
        videos = []

        for key in history:
            for k in key.keys():
                #print(k)
                result = collection_name.find_one({'videoInfo.id': k})
                if result:
                    json_video = {
                        "id": k,
                        "title": result['videoInfo']['snippet']['title'],
                        "timing": key[k]['date_time'],
                        "Day": key[k]['weekday']
                    }
                    videos.append(json_video)
        # #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def get_likes(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        liked = user_doc['user']['Liked_Videos']
        #print(liked)
        videos = []

        for key in liked:
            result = collection_name.find_one({'videoInfo.id': key})
            if result:
                json_video = {
                    "id": key,
                    "title": result['videoInfo']['snippet']['title'],
                }
                videos.append(json_video)
        #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def get_playlist(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        playlist = user_doc['user']['playlist']
        #print(playlist)
        videos = []

        for key in playlist:
            result = collection_name.find_one({'videoInfo.id': key})
            if result:
                json_video = {
                    "id": key,
                    "title": result['videoInfo']['snippet']['title'],
                }
                videos.append(json_video)
        #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def get_uploaded_videos(request, username):
    collection_name_user = connect_user()
    collection_name = connect()
    #print(username)
    user_doc = collection_name_user.find_one({'user.username': username})
    if user_doc:
        #print(1)
        upload_video = user_doc['user']['uploaded_videos']
        #print(upload_video)
        videos = []

        for key in upload_video:
            result = collection_name.find_one({'videoInfo.id': key})
            if result:
                json_video = {
                    "id": key,
                    "title": result['videoInfo']['snippet']['title'],
                }
                videos.append(json_video)
        #print(videos)
        return JsonResponse(videos, safe=False)

    return JsonResponse({"error": "User not found"}, status=404)

@require_GET
def video_suggestion(request, videoID):
    collection_name = connect()
    collection_name_user = connect_user()
    graph = Neo4j_Graph(collection_name)
    # if request.method=='GET':
    # videoID = request.POST.get('videoID', '')
    # #print("HELLO")
    list_of_suggestions = graph.get_suggestions(videoID)
    # #print("HELLO2 0000")
    # #print(list_of_suggestions)
    user_profile = MyUser.objects.get(username=request.user)
    #print(user_profile.email)

    user_doc = collection_name_user.find_one({'user.username': user_profile.username})
    #print(collection_name_user)

    dislike = user_doc['user']['Disliked_Videos']
    #print(dislike)
    
    suggest=[]
    for video_id in list_of_suggestions:
        # video = Video.objects.get(video_id=video_id)
        result = collection_name.find_one({'videoInfo.id': video_id})
        if result not in suggest and video_id not in dislike:
            suggest.append(result)
    # #print(suggest)
    search_results = [
            {**doc, 'videoInfo': {**doc['videoInfo'], '_id': str(doc['_id'])}} for doc in suggest
        ]
    response_data = {'suggestions': search_results}
    
    # return JsonResponse(response_data, safe=False)
    return JsonResponse(response_data, encoder=MongoEncoder, safe=False)

    # Handle other HTTP methods or invalid requests
    # return JsonResponse({'error': 'Invalid request'}, status=400)

# @require_GET
# def favorite_video(request, video_id, action):
#     #print(1)
#     collection_name = connect()
#     # Your logic to add/remove the video from favorites based on the action
#     # This function should handle adding/removing a video from favorites based on the video_id and action parameters
#     result = collection_name.find_one({'videoInfo.id': video_id})
#     if result:
#         statistics = result.get('videoInfo', {}).get('statistics', {})
#         favorite = statistics.get('favoriteCount', 0)  # Default value is 0 if not found

#         if action == 'add':
#             new_favorite_count = favorite + 1
#             collection_name.update_one(
#                 {'videoInfo.id': video_id},
#                 {'$set': {'videoInfo.statistics.favoriteCount': new_favorite_count}}
#             )
#             # Perform other operations if needed

#         return JsonResponse({'success': True})
#     else:
#         return JsonResponse({'success': False, 'error': 'Video not found'})

# @require_GET
# def home(request):

#     # Connect to MongoDB
#     # client = MongoClient('mongodb://localhost:27017/')
#     # db = client['your_database_name']  # Replace 'your_database_name' with your actual database name
#     # collection = db['your_collection_name']  # Replace 'your_collection_name' with your actual collection name
#     directory = "api/test"
#     # def insert_json_files(directory):
#     #print(directory)
#     for root, dirs, files in os.walk(directory):
#         #print(216)
#         for file in files:
#             #print(218)
#             if file.endswith(".json"):
#                 file_path = os.path.join(root, file)
#                 with open(file_path, 'r') as json_file:
#                     try:
#                         json_data = json.load(json_file)

#                         title = json_data['videoInfo']['snippet']['title']
#                         video_id = json_data['videoInfo']['id']
#                         likes = int(json_data['videoInfo']['statistics']['likeCount'])
#                         dislikes = json_data['videoInfo']['statistics']['dislikeCount']
#                         views = json_data['videoInfo']['statistics']['viewCount']
#                         video = Video(title=title, video_id=video_id, likes=likes, dislikes=dislikes, views=views)
#                         video.save()
#                         #print(video.views)
#                         # Insert the JSON data into MongoDB
#                         # collection.insert_one(json_data)
#                         # #print(f"Inserted data from {file_path} into MongoDB")
#                     except Exception as e:
#                         #print(f"Error inserting data from {file_path} into MongoDB: {e}")
#     return HttpResponse("Data inserted successfully")
#     # Specify the directory containing your JSON files
#      # Replace with the actual path

#     # Call the function to insert JSON files into MongoDB
#     # insert_json_files(directory_path)

