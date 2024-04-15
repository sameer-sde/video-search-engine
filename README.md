# Video Player

## Demo Video of the application
[Demo Video](https://drive.google.com/file/d/1xYjWtHXtbQzt_JXsIeXxIG1DCoaUsJ0k/view?usp=sharing)

## Setup

### Clone the repository
```bash 
git clone https://github.com/Ris-code/Video_player_backend_database.git
```

### Install pipenv
```bash
pip install pipenv
```
or

```bash
pip3 install pipenv
```

### Get into the environment
```bash
pipenv shell
```

### Install the dependencies
```bash
pipenv install
```

#### Get into the directory having manage.py

### Run the server
```bash
python manage.py runserver
```

### To setup mongoDB

- Create a .env file
- Get the connection string from your localhost mongoDB or cloud hosted mongoDB
- In the .env file store it in a variable name ```Connection_string```
- Now from the profile section of our application you can upload this [test video data](video_search_engine/api/test) from upload json option

### To setup Neo4J

- Navigate to code file [video_graph.py](video_search_engine/api/video_graph.py)
- Connect with neo4j in your localhost using database name and password
- Create an object of class Neo4j_Graph and then call the following mentioned functions in order
  - ```create_node``` - for creating nodes in neo4j graph for all videos in test_data 
  - ```make_connections``` - for creating connection of all vidoes in test_data
- This will create the relationship between the nodes
- *Note : Building relationship between the nodes in neo4j will take some time
