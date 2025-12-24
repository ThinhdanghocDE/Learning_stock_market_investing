# Frontend - Learning Stock Market Investing

Frontend React application cho hệ thống học và thực hành đầu tư chứng khoán.

## Công nghệ sử dụng

- **React 18** - UI framework
- **Vite** - Build tool và dev server
- **React Router** - Routing
- **Zustand** - State management
- **Axios** - HTTP client
- **Lightweight Charts** - TradingView charts
- **CSS Modules** - Styling

## Cấu trúc thư mục

```
frontend/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Auth/           # Authentication components
│   │   └── Layout/         # Layout components
│   ├── pages/              # Page components
│   │   ├── Auth/          # Login, Register
│   │   ├── Dashboard/      # Dashboard page
│   │   ├── Trading/        # Trading page với charts
│   │   ├── Learning/       # Learning pages
│   │   └── Portfolio/     # Portfolio page
│   ├── stores/             # Zustand stores
│   │   └── authStore.js   # Authentication state
│   ├── utils/              # Utilities
│   │   ├── api.js         # Axios instance
│   │   └── websocket.js   # WebSocket client
│   ├── App.jsx             # Main app component
│   ├── main.jsx            # Entry point
│   └── index.css           # Global styles
├── index.html
├── package.json
└── vite.config.js
```

## Cài đặt

```bash
cd frontend
npm install
```

## Chạy development server

```bash
npm run dev
```

Server sẽ chạy tại `http://localhost:3000`

## Build production

```bash
npm run build
```

Output sẽ ở trong thư mục `dist/`

## Tính năng

### Đã hoàn thành

- [x] Authentication (Login/Register)
- [x] Protected Routes
- [x] Layout với Navigation
- [x] Dashboard
- [x] Trading Page với Chart (cơ bản)
- [x] Learning Pages
- [x] Portfolio Page
- [x] WebSocket integration (cơ bản)

### Đang phát triển

- [ ] Trading Panel (đặt lệnh)
- [ ] Real-time chart updates
- [ ] Lesson detail với chart
- [ ] AI Coach chat panel

## Environment Variables

Tạo file `.env` trong thư mục `frontend/`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## API Integration

Frontend kết nối với Backend API tại `http://localhost:8000/api`

WebSocket kết nối tại `ws://localhost:8000/ws`

Proxy được cấu hình trong `vite.config.js` để tự động forward requests.

