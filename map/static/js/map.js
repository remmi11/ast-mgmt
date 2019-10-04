function toWKT(layer) {
    var lng, lat, coords = [];
    if (layer instanceof L.Polygon || layer instanceof L.Polyline) {
        var latlngs = layer.getLatLngs();
        for (var i = 0; i < latlngs.length; i++) {
	    	latlngs[i]
	    	coords.push(latlngs[i].lng + " " + latlngs[i].lat + " 0");
	        if (i === 0) {
	        	lng = latlngs[i].lng;
	        	lat = latlngs[i].lat;
	        }
	};
        if (layer instanceof L.Polygon) {
            return "POLYGON ((" + coords.join(",") + "," + lng + " " + lat + "))";
        } else if (layer instanceof L.Polyline) {
            return "LINESTRING (" + coords.join(",") + ")";
        }
    } else if (layer instanceof L.Marker) {
        return "MULTIPOINT (" + layer.getLatLng().lng + " " + layer.getLatLng().lat + ")";
    }
}

var map = L.map('map-background').setView([51.505, -0.09], 8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

var drawnItems = new L.FeatureGroup().addTo(map);
var drawControl = new L.Control.Draw({
	draw: {
		polyline: true,
		polygon: false,
		rectangle: false,
		circle: false,
		circlemarker: false,
		marker: true,
	},
	edit: {
		featureGroup: drawnItems,
		edit: false
	}
}).addTo(map);