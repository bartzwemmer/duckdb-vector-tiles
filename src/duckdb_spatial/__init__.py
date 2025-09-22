import duckdb
import flask

# Import the database
from db import init_database

# Initialize Flask app
app = flask.Flask(__name__)

database_location = "tiles.db"


# Tile endpoint to serve vector tiles
@app.route('/tiles/<int:z>/<int:x>/<int:y>.pbf')
def get_tile(z, x, y):
    con = duckdb.connect(database_location, True)
    con.execute("load spatial")
    # Query to get the tile data from DuckDB
    # - Note that the geometry in table `monuments` is assumed to be projected to `EPSG:3857` (Web Mercator)
    # - You may want to create an R-Tree index on the geometry column, or create a separate bounding box struct column
    #   to perform range-filtering, or somehow pre-filter the geometries some other way before feeding them into 
    #   ST_AsMVTGeom if your dataset is large (and on disk)

    # Use con.cursor() to avoid threading issues with Flask
    with con.cursor() as local_con:
        tile_blob = local_con.execute("""
            SELECT ST_AsMVT({
                "Monument number": rijksmonument_nummer,
                "Url": concat('<a href="', rijksmonumenturl, '" target="_blank"">link</a>'),
                "geom": ST_AsMVTGeom(
                    geom,
                    ST_Extent(ST_TileEnvelope($1, $2, $3))
                    )
                })
            FROM monuments
            WHERE ST_Intersects(geom, ST_TileEnvelope($1, $2, $3))
            """, [z, x, y]).fetchone()

        # Send the tile data as a response
        tile = tile_blob[0] if tile_blob and tile_blob[0] else b''
        return flask.Response(tile, mimetype='application/x-protobuf')


# HTML content for the index page
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DuckDB Vector Tile Demo</title>
    <link rel="icon" type="image/x-icon" href="https://onegiantleap.dev/wp-content/uploads/2024/01/ogl-letter-logo-design-with-polygon-shape-ogl-polygon-and-cube-shape-logo-design-ogl-hexagon-logo-template-white-and-black-colors-ogl-monogram-business-and-real-estate-logo-vector.png">
    <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
    <script src='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js'></script>
    <link href='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css' rel='stylesheet' />
    <style>
        body { margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        #floating-textbox {
            position: absolute;
            top: 30px;
            left: 30px;
            z-index: 1000;
            background: rgba(255,255,255,0.9);
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            padding: 16px;
            width: 250px;
            font-family: Arial, sans-serif;
        }
    </style>
</head>
<body>
<div id="floating-textbox">
    <h3>DuckDB Vector Tiles</h3>
    <p>This is a simple demo of how to use the new Vector Tiles option from the DuckDB Spatial extension in a Flask app. Support was added in version 1.4 of DuckDB.</p>
    <p>Use the map to explore the vector tiles generated from the DuckDB database. It shows the national monuments of The Netherlands.</p>
    <p>Read the accompanying <a href="https://onegiantleap.dev/duckdb-vector-tiles-demo/" target="_blank">blog post here.</a></p>
</div>
<div id="map"></div>
<script>
    const map = new maplibregl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                'buildings': {
                    type: 'vector',
                    tiles: [`${window.location.origin}/tiles/{z}/{x}/{y}.pbf`],
                    minzoom: 10
                },
                // Also use a public open source basemap
                'osm': {
                    type: 'raster',
                    tiles: [
                        'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                        'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
                        'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'
                    ],
                    tileSize: 256,
                    minzoom: 10
                }
            },
            layers: [
                {
                    id: 'background',
                    type: 'background',
                    paint: { 'background-color': '#a0c8f0' }
                },
                {
                    id: 'osm',
                    type: 'raster',
                    source: 'osm',
                    minzoom: 10,
                    maxzoom: 19
                },
                {
                    id: 'buildings-fill',
                    type: 'fill',
                    source: 'buildings',
                    'source-layer': 'layer',
                    paint: {
                        'fill-color': 'brown',
                        'fill-opacity': 0.6,
                        'fill-outline-color': '#ffffff'
                    }
                },
                {
                    id: 'buildings-stroke',
                    type: 'line',
                    source: 'buildings',
                    'source-layer': 'layer',
                    paint: {
                        'line-color': 'black',
                        'line-width': 0.5
                    }
                }
            ]
        },
        // Zoom in on Amsterdam
        center: [4.9041, 52.3676],
        zoom: 12
    });
    map.addControl(new maplibregl.NavigationControl());
    // Add click handler to show feature properties
    map.on('click', 'buildings-fill', (e) => {
        const coordinates = e.lngLat;
        const properties = e.features[0].properties;
        let popupContent = '<h3>Building Properties</h3>';
        for (const [key, value] of Object.entries(properties)) {
            popupContent += `<p><strong>${key}:</strong> ${value}</p>`;
        }
        new maplibregl.Popup()
            .setLngLat(coordinates)
            .setHTML(popupContent)
            .addTo(map);
    });
    // Change cursor on hover
    map.on('mouseenter', 'buildings-fill', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'buildings-fill', () => {
        map.getCanvas().style.cursor = '';
    });
</script>
</body>
</html>
"""

# Serve the static HTML file for the index page
@app.route("/")
def index():
    return flask.Response(INDEX_HTML, mimetype='text/html')

def run():
    init_database(database_location)
    # Force Flask to wait until the database is initialized
    app.run(debug=True)


if __name__ == '__main__':
    # Start on localhost
    run()