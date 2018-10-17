// creating the map
var map = L.map('map', {
    zoom: 2,
    fullscreenControl: true,
    timeDimension: true,
    timeDimensionOptions: 10000,
    timeDimensionControl: true,
    timeDimensionControlOptions: {
        position: "bottomleft",
        autoPlay: true,
        loopButton: true,
        backwardButton: true,
        forwardButton: true,
        timeSliderDragUpdate: true,
        minSpeed: 1,
        maxSpeed: 6,
        speedStep: 1,
    },
    center: [20, 0],
});


// create the basemap layers (default basemap is world imagery)
var Esri_WorldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(map);
var Esri_WorldTerrain = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}', {maxZoom: 13});
var openStreetMap = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
   attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
   name: 'openStreetMap',
    });


// Add controls for user drawings
var drawnItems = new L.FeatureGroup();      // FeatureGroup is to store editable layers
map.addLayer(drawnItems);

var drawControl = new L.Control.Draw({
    edit: {
        featureGroup: drawnItems,
        edit: false,
    },
    draw: {
        polyline: false,
        circlemarker:false,
        circle:false,
        polygon:false,
        rectangle:false,
    },
});
map.addControl(drawControl);


// Listeners that control what happens when the user draws things on the map
map.on("draw:drawstart ", function (e) {
    drawnItems.clearLayers();
});
map.on("draw:created", function (e) {
    var layer = e.layer;
    layer.addTo(drawnItems);
});


function newLayer(variable, color) {
    url = thredds_wms;
    wmsLayer = L.tileLayer.wms(url, {
        layers: variable,
        format: 'image/png',
        transparent: true,
        BGCOLOR:'0x000000',
        opacity: $("#opacity").val(),
        styles: 'boxfill/' + color,
        colorscalerange: '215,325'
        });

    timedLayer = L.timeDimension.layer.wms(wmsLayer, {
        name: 'TimeSeries',
        requestTimefromCapabilities: true,
        updateTimeDimension: true,
        updateTimeDimensionMode: 'replace',
        cache: 15,
        }).addTo(map);
}


// removes old controls and adds new ones. Must be called after changeLayer
function newControls(basemaps) {
    data_layers = {
        'GLDAS Layer': timedLayer,
        }
    basemaps = {
        "ESRI Imagery": Esri_WorldImagery,
        "ESRI Terrain": Esri_WorldTerrain,
        "OpenStreetMap": openStreetMap,
        }
    lyrControls = L.control.layers(basemaps, data_layers).addTo(map);
}


function clearmap() {
    lyrControls.removeLayer(timedLayer);
    map.removeLayer(wmsLayer);
    map.removeLayer(timedLayer)
    map.removeControl(lyrControls)
}


function getLegend(variable, color) {
    url = thredds_wms
    url += "?REQUEST=GetLegendGraphic&LAYER=" + variable + "&PALETTE=" + color + "&COLORSCALERANGE=215,325";
    lookup = '<img src="' + url + '" alt="legend" style="width:100%; float:right;">'
    document.getElementById("legend").innerHTML = lookup;
}


function updateMap() {
    variable = $('#layers').val();
    time = $("#times").val();
    color= $('#colors').val();
    clearmap();
    newLayer(variable, color);
    newControls();
    getLegend(variable, color);
}