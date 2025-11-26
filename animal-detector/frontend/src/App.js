import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import { GeoSearchControl, OpenStreetMapProvider } from 'leaflet-geosearch';
import L from 'leaflet';

// Fix for broken marker images in React-Leaflet
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});
// End of fix

// Component to handle map view changes
function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// Component for the search bar
function SearchField({ onLocationFound }) {
  const map = useMap();

  useEffect(() => {
    const provider = new OpenStreetMapProvider();
    const searchControl = new GeoSearchControl({
      provider: provider,
      style: 'bar',
      showMarker: false,
      showPopup: false,
      autoClose: true,
      retainZoomLevel: false,
      animateZoom: true,
      keepResult: true,
    });

    map.addControl(searchControl);

    const onResult = (result) => {
      onLocationFound({ lat: result.location.y, lng: result.location.x });
    };

    map.on('geosearch/showlocation', onResult);

    return () => {
      map.removeControl(searchControl);
      map.off('geosearch/showlocation', onResult);
    };
  }, [map, onLocationFound]);

  return null;
}

// Component to handle marker placement
function LocationPicker({ isPlacing, onPlacement }) {
  useMapEvents({
    click(e) {
      if (isPlacing) {
        onPlacement(e.latlng);
      }
    },
  });
  return null;
}


function App() {
  const [imageSrc, setImageSrc] = useState(null);
  const [loadedImage, setLoadedImage] = useState(null);
  const [boxes, setBoxes] = useState([]);
  const [drawing, setDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentBox, setCurrentBox] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [position, setPosition] = useState({ lat: -34.6037, lng: -58.3816 });
  const [isPlacingMarker, setIsPlacingMarker] = useState(false);
  const [embedCode, setEmbedCode] = useState('');
  const canvasRef = useRef(null);
  const mapRef = useRef(null);

  // Effect for loading the image object from src
  useEffect(() => {
    if (!imageSrc) return;
    const img = new Image();
    img.src = imageSrc;
    img.onload = () => {
      setLoadedImage(img);
    };
  }, [imageSrc]);

  // Effect to change map cursor based on placement mode
  useEffect(() => {
    const map = mapRef.current;
    if (map) {
      const container = map.getContainer();
      if (isPlacingMarker) {
        container.style.cursor = 'crosshair';
      } else {
        container.style.cursor = 'grab';
      }
    }
  }, [isPlacingMarker]);

  // Effect to generate embed code
  useEffect(() => {
    const { lat, lng } = position;
    const code = `
<iframe 
  width="100%" 
  height="100%" 
  frameborder="0" 
  scrolling="no" 
  marginheight="0" 
  marginwidth="0" 
  src="https://maps.google.com/maps?q=${lat},${lng}&hl=es&z=14&amp;output=embed"
>
</iframe>`;
    setEmbedCode(code.trim());
  }, [position]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageSrc(URL.createObjectURL(file));
      setBoxes([]);
    }
  };

  const handleMouseDown = (e) => {
    if (!loadedImage) return;
    setDrawing(true);
    const pos = getCanvasCoordinates(e);
    setStartPos(pos);
    setCurrentBox({ x1: pos.x, y1: pos.y, x2: pos.x, y2: pos.y, name: '' });
  };

  const handleMouseMove = (e) => {
    if (!drawing || !loadedImage) return;
    const pos = getCanvasCoordinates(e);
    setCurrentBox(prevBox => ({ ...prevBox, x2: pos.x, y2: pos.y }));
  };

  const handleMouseUp = () => {
    if (!drawing || !loadedImage) return;
    setDrawing(false);
    if (currentBox) {
      const name = prompt('Enter animal name:');
      if (name) {
        setBoxes(prevBoxes => [...prevBoxes, { ...currentBox, name, date: selectedDate }]);
      }
      setCurrentBox(null);
    }
  };

  const getCanvasCoordinates = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const handleSave = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = 'annotated_image.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  const handleSaveToDB = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const image = canvas.toDataURL('image/png');

    try {
      await axios.post('http://127.0.0.1:8000/save_annotation/', {
        image: image,
        boxes: boxes,
        latitude: position.lat,
        longitude: position.lng,
      });
      alert('Annotation saved to database!');
    } catch (error) {
      console.error('Error saving annotation:', error);
      alert('Error saving annotation.');
    }
  };

  const handlePlacement = (latlng) => {
    setPosition(latlng);
    setIsPlacingMarker(false);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(embedCode).then(() => {
      alert('Código copiado al portapapeles!');
    }, (err) => {
      console.error('Could not copy text: ', err);
    });
  };

  // Effect for drawing on the canvas
  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    if (loadedImage) {
      canvas.width = loadedImage.width;
      canvas.height = loadedImage.height;
      context.drawImage(loadedImage, 0, 0);
    } else {
      context.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    // Draw saved boxes and their info
    boxes.forEach(box => {
      const { x1, y1, x2, y2, name, date } = box;
      const boxY = Math.max(y1, y2);

      context.strokeStyle = '#00FF00';
      context.lineWidth = 2;
      context.strokeRect(x1, y1, x2 - x1, y2 - y1);
      
      context.fillStyle = '#00FF00';
      context.font = '18px Arial';
      context.fillText(name, x1, y1 > 20 ? y1 - 10 : y1 + 20);
      
      context.font = '14px Arial';
      context.fillText(date, x1, boxY + 20);

      if (position) {
        context.font = '12px Arial';
        context.fillText(`Lat: ${position.lat.toFixed(4)}`, x1, boxY + 35);
        context.fillText(`Lng: ${position.lng.toFixed(4)}`, x1, boxY + 50);
      }
    });

    if (currentBox) {
      context.strokeStyle = '#00FF00';
      context.lineWidth = 2;
      context.strokeRect(currentBox.x1, currentBox.y1, currentBox.x2 - currentBox.x1, currentBox.y2 - currentBox.y1);
    }

  }, [loadedImage, boxes, currentBox, position]);

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4">Anotador de Imágenes</h1>
      <div className="row">
        <div className="col-md-6">
          <div className="card mb-4">
            <div className="card-body">
              <h5 className="card-title">Sube una imagen</h5>
              <div className="mb-3">
                <input className="form-control" type="file" onChange={handleFileChange} />
              </div>
              <div className="mb-3">
                <label htmlFor="date-input" className="form-label">Fecha</label>
                <input
                  id="date-input"
                  className="form-control"
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
              <button className="btn btn-success" onClick={handleSave}>Guardar Imagen</button>
              <button className="btn btn-info ms-2" onClick={handleSaveToDB}>Guardar en Base de Datos</button>
            </div>
          </div>
          <div className="card">
            <div className="card-body">
              <h5 className="card-title d-flex justify-content-between align-items-center">
                Geolocalización
                <button 
                  className={`btn btn-sm ${isPlacingMarker ? 'btn-success' : 'btn-outline-primary'}`} 
                  title="Posicionar Marcador"
                  onClick={() => setIsPlacingMarker(true)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-geo-alt-fill" viewBox="0 0 16 16">
                    <path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10zm0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/>
                  </svg>
                </button>
              </h5>
              <div className="row">
                <div className="col-md-6">
                  <label htmlFor="lat-input" className="form-label">Latitud</label>
                  <input
                    id="lat-input"
                    className="form-control"
                    type="number"
                    step="any"
                    value={position.lat}
                    onChange={(e) => setPosition({ ...position, lat: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="col-md-6">
                  <label htmlFor="lng-input" className="form-label">Longitud</label>
                  <input
                    id="lng-input"
                    className="form-control"
                    type="number"
                    step="any"
                    value={position.lng}
                    onChange={(e) => setPosition({ ...position, lng: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
              <div className="mt-3" style={{ height: '400px', width: '100%' }}>
                <MapContainer ref={mapRef} center={[position.lat, position.lng]} zoom={13} style={{ height: '100%', width: '100%' }}>
                  <ChangeView center={[position.lat, position.lng]} zoom={13} />
                  <TileLayer
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
                  />
                  <Marker position={position}></Marker>
                  <LocationPicker isPlacing={isPlacingMarker} onPlacement={handlePlacement} />
                  <SearchField onLocationFound={setPosition} />
                </MapContainer>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Imagen</h5>
              <canvas
                ref={canvasRef}
                className="img-fluid"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
              />
            </div>
          </div>
        </div>
      </div>
      <div className="row mt-4">
        <div className="col-md-12">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Código para Embeber</h5>
              <p>Usa este código para incrustar el mapa con la ubicación actual en tu sitio web.</p>
              <textarea
                className="form-control"
                rows="5"
                readOnly
                value={embedCode}
              />
              <button className="btn btn-primary mt-2" onClick={copyToClipboard}>
                Copiar Código
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
