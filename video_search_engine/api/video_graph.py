from pymongo import MongoClient
from neo4j import GraphDatabase
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from django.conf import settings

nltk.download('stopwords')
nltk.download('punkt')

# Use Django settings for Mongo connection instead of hardcoded URI
connect_string = settings.MONGO_CONNECTION_STRING
my_client = MongoClient(connect_string)

# client = MongoClient('localhost', 27017)

# db = client['DE']

# collection = db['video']
dbname = my_client['Video']

# Now get/create collection name
collection = dbname["Set_of_videos"]


class Neo4j_Graph:
    def __init__(self, collection):
        self.all_documents = list(collection.find())
        self.collection = collection
        self.__url = "bolt://localhost:7687"
        self.__username = "neo4j"
        self.__password = "password"

    def execute_query(self, query, parameters=None):
        with GraphDatabase.driver(self.__url, auth=(self.__username, self.__password)) as driver:
            with driver.session() as session:
                result = session.run(query, parameters)
                return result

    def create_node(self):
        all_documents = self.all_documents
        for i in all_documents:
            try:
                id_ = i['videoInfo']['id']
                comment_count = i['videoInfo']['statistics']['commentCount']
                view_count = i['videoInfo']['statistics']['viewCount']
                favourite_count = i['videoInfo']['statistics']['favoriteCount']
                dislike_count = i['videoInfo']['statistics']['dislikeCount']
                like_count = int(i['videoInfo']['statistics']['likeCount'])
            except:
                continue
            query = (
                f"CREATE (n:video_node {{ id_: '{id_}', "
                f"commentCount: {comment_count}, "
                f"viewCount: {view_count}, "
                f"favoriteCount: {favourite_count}, "
                f"dislikeCount: {dislike_count}, "
                f"likeCount: {like_count} }})"
            )
            self.execute_query(query)

    def create_new_node(self, video_id1):
        all_documents = self.all_documents
        for i in all_documents:
            id_ = i['videoInfo']['id']
            if id_ == video_id1:
                comment_count = i['videoInfo']['statistics']['commentCount']
                view_count = i['videoInfo']['statistics']['viewCount']
                favourite_count = i['videoInfo']['statistics']['favoriteCount']
                dislike_count = i['videoInfo']['statistics']['dislikeCount']
                like_count = int(i['videoInfo']['statistics']['likeCount'])
                query = (
                    f"CREATE (n:video_node {{ id_: '{id_}', "
                    f"commentCount: {comment_count}, "
                    f"viewCount: {view_count}, "
                    f"favoriteCount: {favourite_count}, "
                    f"dislikeCount: {dislike_count}, "
                    f"likeCount: {like_count} }})"
                )
                self.execute_query(query)
                break

    def tag_connection_priority(self, tag1, tag2):
        priority = 0
        for tag in tag1:
            if tag in tag2:
                priority += 1
        return priority

    def title_connection_priority(self, title1, title2):
        priority = 0
        for i in title1:
            for j in title2:
                if i.lower() == j.lower():
                    if i.lower() not in stopwords.words('english'):
                        priority += 1
        return priority

    def description_connection_priority(self, description1, description2):
        priority = 0
        for i in description1:
            for j in description2:
                if i.lower() == j.lower():
                    if i.lower() not in stopwords.words('english'):
                        priority += 1
        return priority

    def make_connections(self):
        all_documents = self.all_documents
        for i in range(len(all_documents)):
            try:
                video_id1 = all_documents[i]['videoInfo']['id']
            except:
                continue
            edge_node_list = []
            try:
                tag1 = [t.lower().split(" ") for t in all_documents[i]['videoInfo']['snippet']['tags']]
                tag1 = list(set([item for sublist in tag1 for item in sublist]))
            except:
                tag1 = []

            try:
                title1 = all_documents[i]['videoInfo']['snippet']['title'].split(" ")
            except:
                title1 = []
            try:
                description1 = all_documents[i]['videoInfo']['snippet']['description'].split(" ")
            except:
                description1 = []
            for j in range(len(all_documents)):
                if i == j:
                    continue
                edge_priority = 0
                try:
                    tag2 = [t.lower().split(" ") for t in all_documents[j]['videoInfo']['snippet']['tags']]
                    tag2 = list(set([item for sublist in tag2 for item in sublist]))
                except:
                    tag2 = []

                try:
                    title2 = all_documents[j]['videoInfo']['snippet']['title'].split(" ")
                except:
                    title2 = []

                try:
                    description2 = all_documents[j]['videoInfo']['snippet']['description'].split(" ")
                except:
                    description2 = []

                edge_priority += self.tag_connection_priority(tag1, tag2)
                edge_priority += self.title_connection_priority(title1, title2)
                edge_priority += self.description_connection_priority(description1, description2)

                if edge_priority > 0:
                    try:
                        view_count = all_documents[j]['videoInfo']['statistics']['viewCount']
                    except:
                        view_count = 0
                    try:
                        fav_count = all_documents[j]['videoInfo']['statistics']['favouriteCount']
                    except:
                        fav_count = 0
                    try:
                        like_count = int(all_documents[j]['videoInfo']['statistics']['likeCount'])
                    except:
                        like_count = 0
                    try:
                        dislike_count = all_documents[j]['videoInfo']['statistics']['dislikeCount']
                    except:
                        dislike_count = 0
                    value = view_count + fav_count + like_count - 2 * dislike_count
                    priority = [edge_priority, value]
                    channel1 = all_documents[i]['videoInfo']['snippet']['channelTitle']
                    channel2 = all_documents[j]['videoInfo']['snippet']['channelTitle']
                    if channel1 == channel2:
                        edge_priority *= 2
                    edge_node_list.append([priority, j])
            edge_node_list.sort()
            edge_node_list = edge_node_list[::-1]
            top_10_videos = edge_node_list[:10]

            for e_j in top_10_videos:
                j = e_j[1]
                video_id2 = all_documents[j]['videoInfo']['id']
                priority = e_j[0][0] + e_j[0][1]
                query = (
                    f"MATCH (v1:video_node {{id_: '{video_id1}'}}), "
                    f"(v2:video_node {{id_: '{video_id2}'}}) "
                    "MERGE (v1)-[c:connection]->(v2) "
                    f"ON CREATE SET c.priority = {priority} "
                    "ON MATCH SET c.priority = c.priority + " + str(priority) + ";"
                )
                self.execute_query(query)

    def create_connection_for_new_video(self, video_id1):
        i = -1
        all_documents = self.all_documents
        for k in range(len(all_documents)):
            if all_documents[k]['videoInfo']['id'] == video_id1:
                i = k
        if i == -1:
            print("InValid Video Id")
            return
        edge_node_list = []
        try:
            tag1 = [t.lower().split(" ") for t in all_documents[i]['videoInfo']['snippet']['tags']]
            tag1 = list(set([item for sublist in tag1 for item in sublist]))
        except:
            tag1 = []

        try:
            title1 = all_documents[i]['videoInfo']['snippet']['title'].split(" ")
        except:
            title1 = []
        try:
            description1 = all_documents[i]['videoInfo']['snippet']['description'].split(" ")
        except:
            description1 = []
        for j in range(len(all_documents)):
            if i == j:
                continue
            edge_priority = 0
            try:
                tag2 = [t.lower().split(" ") for t in all_documents[j]['videoInfo']['snippet']['tags']]
                tag2 = list(set([item for sublist in tag2 for item in sublist]))
            except:
                tag2 = []

            try:
                title2 = all_documents[j]['videoInfo']['snippet']['title'].split(" ")
            except:
                title2 = []

            try:
                description2 = all_documents[j]['videoInfo']['snippet']['description'].split(" ")
            except:
                description2 = []

            edge_priority += self.tag_connection_priority(tag1, tag2)
            edge_priority += self.title_connection_priority(title1, title2)
            edge_priority += self.description_connection_priority(description1, description2)

            if edge_priority > 0:
                try:
                    view_count = all_documents[j]['videoInfo']['statistics']['viewCount']
                except:
                    view_count = 0
                try:
                    fav_count = all_documents[j]['videoInfo']['statistics']['favouriteCount']
                except:
                    fav_count = 0
                try:
                    like_count = int(all_documents[j]['videoInfo']['statistics']['likeCount'])
                except:
                    like_count = 0
                try:
                    dislike_count = all_documents[j]['videoInfo']['statistics']['dislikeCount']
                except:
                    dislike_count = 0
                value = view_count + fav_count + like_count - 2 * dislike_count
                priority = [edge_priority, value]
                channel1 = all_documents[i]['videoInfo']['snippet']['channelTitle']
                channel2 = all_documents[j]['videoInfo']['snippet']['channelTitle']
                if channel1 == channel2:
                    edge_priority *= 2
                edge_node_list.append([priority, j])
        edge_node_list.sort()
        edge_node_list = edge_node_list[::-1]
        top_10_videos = edge_node_list[:10]
        for e_j in top_10_videos:
            j = e_j[1]
            video_id2 = all_documents[j]['videoInfo']['id']
            priority = e_j[0][0] + e_j[0][1]
            query = (
                f"MATCH (v1:video_node {{id_: '{video_id1}'}}), "
                f"(v2:video_node {{id_: '{video_id2}'}}) "
                "MERGE (v1)-[c:connection]->(v2) "
                f"ON CREATE SET c.priority = {priority} "
                "ON MATCH SET c.priority = c.priority + " + str(priority) + ";"
            )
            self.execute_query(query)

    def get_suggestions(self, video_id):
        query = (
            f"MATCH (n)-[r:connection]->(connected_node) "
            f"WHERE n.id_ = '{video_id}' "
            "RETURN connected_node.id_ AS video_id "
            "ORDER BY r.priority DESC;"
        )
        suggested_video_id = []

        with GraphDatabase.driver(self.__url, auth=(self.__username, self.__password)) as driver:
            with driver.session() as session:
                result = session.run(query)
                for record in result:
                    video_id_res = record['video_id']
                    suggested_video_id.append(video_id_res)
        return suggested_video_id

    def suggest_video(self):
        all_documents = self.all_documents
        video_suggestions = {}
        for i in range(len(all_documents)):
            video_id = all_documents[i]['videoInfo']['id']
            suggestions = self.get_suggestions(video_id)
            video_suggestions[video_id] = suggestions
        return video_suggestions

    def update_node(self, video_id, property_name):
        query = (
            "MATCH (n:video_node) WHERE n.id_ = $video_id "
            f"SET n.{property_name} = n.{property_name} + 1 "
            "RETURN n"
        )
        parameters = {"video_id": video_id}
        self.execute_query(query, parameters)

# G = Neo4j_Graph(collection=collection)
# G.create_node()
# G.make_connections()
# print(G.suggest_video())
