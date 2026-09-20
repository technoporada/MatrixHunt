import React, { useState, useEffect, useRef } from 'react';
import { Monitor, Shield, Zap, Terminal, Globe, Lock, Eye, EyeOff } from 'lucide-react';

const MatrixBrowser = () => {
  const [activeTab, setActiveTab] = useState('steam');
  const [isSecureMode, setIsSecureMode] = useState(true);
  const [showCredentials, setShowCredentials] = useState(false);
  const [browserUrl, setBrowserUrl] = useState('');
  const [matrixRain, setMatrixRain] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const canvasRef = useRef(null);
  
  const platforms = {
    steam: {
      name: 'Steam',
      url: 'https://store.steampowered.com/login/',
      icon: '🎮',
      color: '#1b2838',
      gradient: 'from-blue-900 to-slate-900'
    },
    epic: {
      name: 'Epic Games',
      url: 'https://www.epicgames.com/id/login',
      icon: '⚡',
      color: '#2a2a2a',
      gradient: 'from-gray-800 to-black'
    },
    gog: {
      name: 'GOG',
      url: 'https://www.gog.com/account/login',
      icon: '🏰',
      color: '#8b4a9c',
      gradient: 'from-purple-900 to-slate-900'
    },
    origin: {
      name: 'EA Origin',
      url: 'https://accounts.ea.com/connect/auth',
      icon: '🎯',
      color: '#ff6600',
      gradient: 'from-orange-800 to-red-900'
    },
    ubisoft: {
      name: 'Ubisoft',
      url: 'https://account.ubisoft.com/login',
      icon: '🎪',
      color: '#0084ff',
      gradient: 'from-blue-800 to-indigo-900'
    },
    itch: {
      name: 'itch.io',
      url: 'https://itch.io/login',
      icon: '🕹️',
      color: '#fa5c5c',
      gradient: 'from-pink-800 to-red-900'
    }
  };

  // Matrix rain effect
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789@#$%^&*()*&^%+-/~{[|`]}";
    const charArray = chars.split("");
    const fontSize = 14;
    const columns = canvas.width / fontSize;
    const drops = [];

    for (let x = 0; x < columns; x++) {
      drops[x] = 1;
    }

    const draw = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      ctx.fillStyle = '#0F0';
      ctx.font = fontSize + 'px monospace';
      
      for (let i = 0; i < drops.length; i++) {
        const text = charArray[Math.floor(Math.random() * charArray.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }
    };

    const interval = setInterval(draw, 33);
    return () => clearInterval(interval);
  }, []);

  const openPlatform = (platformKey) => {
    setIsLoading(true);
    setActiveTab(platformKey);
    setBrowserUrl(platforms[platformKey].url);
    
    // Simulate loading
    setTimeout(() => {
      setIsLoading(false);
    }, 1500);
  };

  const securityFeatures = [
    'Sandbox izolacji procesów',
    'Blokada trackerów',
    'Szyfrowanie SSL/TLS',
    'Ochrona przed fingerprintingiem',
    'Czyszczenie cookies po sesji'
  ];

  return (
    <div className="min-h-screen bg-black text-green-400 font-mono relative overflow-hidden">
      {/* Matrix Background */}
      <canvas 
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none opacity-20 z-0"
      />
      
      {/* Main Interface */}
      <div className="relative z-10 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 bg-black/80 backdrop-blur-sm rounded-lg p-4 border border-green-500/30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-8 h-8 text-green-400" />
              <h1 className="text-2xl font-bold text-green-400 tracking-wider">
                MATRIX-BROWSER
              </h1>
            </div>
            <div className="flex items-center gap-2 text-green-300">
              <Shield className={`w-5 h-5 ${isSecureMode ? 'text-green-400' : 'text-red-400'}`} />
              <span className="text-sm">
                {isSecureMode ? 'SECURE MODE' : 'INSECURE'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSecureMode(!isSecureMode)}
              className={`px-4 py-2 rounded border transition-all ${
                isSecureMode 
                  ? 'border-green-500 bg-green-500/10 text-green-400' 
                  : 'border-red-500 bg-red-500/10 text-red-400'
              }`}
            >
              <Lock className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowCredentials(!showCredentials)}
              className="px-4 py-2 rounded border border-green-500/50 bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-all"
            >
              {showCredentials ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Platform Selector */}
        <div className="mb-6 bg-black/80 backdrop-blur-sm rounded-lg p-4 border border-green-500/30">
          <h2 className="text-lg mb-4 text-green-300 flex items-center gap-2">
            <Globe className="w-5 h-5" />
            GAMING PLATFORMS
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Object.entries(platforms).map(([key, platform]) => (
              <button
                key={key}
                onClick={() => openPlatform(key)}
                className={`p-4 rounded-lg border transition-all duration-300 hover:scale-105 ${
                  activeTab === key
                    ? 'border-green-400 bg-green-400/10 shadow-lg shadow-green-400/25'
                    : 'border-green-500/30 bg-black/50 hover:border-green-400/50'
                }`}
              >
                <div className="text-2xl mb-2">{platform.icon}</div>
                <div className="text-sm text-green-300">{platform.name}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Browser Window */}
        <div className="bg-black/90 backdrop-blur-sm rounded-lg border border-green-500/30 overflow-hidden">
          {/* Browser Header */}
          <div className="bg-gradient-to-r from-green-900/50 to-black p-3 flex items-center justify-between border-b border-green-500/30">
            <div className="flex items-center gap-3">
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <Monitor className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-300">
                  {platforms[activeTab]?.name || 'Matrix Browser'}
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-2 text-xs text-green-400">
              <Zap className="w-4 h-4" />
              <span>ENCRYPTED</span>
            </div>
          </div>

          {/* URL Bar */}
          <div className="bg-black/70 p-3 border-b border-green-500/20">
            <div className="flex items-center bg-black/50 rounded border border-green-500/30 p-2">
              <Lock className="w-4 h-4 text-green-400 mr-2" />
              <input
                type="text"
                value={browserUrl}
                onChange={(e) => setBrowserUrl(e.target.value)}
                className="flex-1 bg-transparent text-green-300 text-sm outline-none placeholder-green-600"
                placeholder="https://..."
              />
              <button className="ml-2 px-3 py-1 bg-green-500/20 text-green-400 rounded text-xs hover:bg-green-500/30 transition-all">
                GO
              </button>
            </div>
          </div>

          {/* Browser Content */}
          <div className="h-96 relative overflow-hidden">
            {isLoading ? (
              <div className="h-full flex items-center justify-center bg-gradient-to-br from-black via-green-900/10 to-black">
                <div className="text-center">
                  <div className="inline-block w-8 h-8 border-2 border-green-400/30 border-t-green-400 rounded-full animate-spin mb-4"></div>
                  <p className="text-green-400 animate-pulse">INITIALIZING SECURE CONNECTION...</p>
                  <div className="mt-2 text-xs text-green-600">
                    [{Array.from({length: 20}).map((_, i) => 
                      <span key={i} className="animate-pulse" style={{animationDelay: `${i * 100}ms`}}>
                        {Math.random() > 0.5 ? '█' : '░'}
                      </span>
                    )}]
                  </div>
                </div>
              </div>
            ) : (
              <div className={`h-full bg-gradient-to-br ${platforms[activeTab]?.gradient || 'from-black to-green-900/20'} flex items-center justify-center`}>
                <div className="text-center max-w-md">
                  <div className="text-6xl mb-4">{platforms[activeTab]?.icon}</div>
                  <h3 className="text-2xl text-green-300 mb-2">{platforms[activeTab]?.name}</h3>
                  <p className="text-green-600 mb-4">Bezpieczne połączenie nawiązane</p>
                  <button
                    onClick={() => window.open(platforms[activeTab]?.url, '_blank')}
                    className="px-6 py-3 bg-green-500/20 border border-green-500 text-green-400 rounded hover:bg-green-500/30 transition-all"
                  >
                    Otwórz w nowej karcie
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Security Panel */}
        {showCredentials && (
          <div className="mt-6 bg-black/80 backdrop-blur-sm rounded-lg p-6 border border-green-500/30">
            <h3 className="text-lg mb-4 text-green-300 flex items-center gap-2">
              <Shield className="w-5 h-5" />
              ZABEZPIECZENIA AKTYWNE
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {securityFeatures.map((feature, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-green-500/10 rounded border border-green-500/20">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-sm text-green-300">{feature}</span>
                </div>
              ))}
            </div>
            
            <div className="mt-6 p-4 bg-black/50 rounded border border-green-500/20">
              <h4 className="text-green-400 mb-2">MANAGER HASEŁ</h4>
              <div className="space-y-2">
                {Object.entries(platforms).map(([key, platform]) => (
                  <div key={key} className="flex items-center justify-between p-2 bg-green-500/5 rounded">
                    <span className="text-green-300">{platform.name}</span>
                    <div className="flex items-center gap-2">
                      <input
                        type="password"
                        placeholder="••••••••"
                        className="bg-black/50 border border-green-500/30 rounded px-2 py-1 text-xs text-green-400 w-24"
                      />
                      <button className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30">
                        SAVE
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MatrixBrowser;