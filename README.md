# LLM Powered Smart Greenhouse Assistant

前端环境：React + JavaScript/JSX + CSS + Recharts，使用 Vite。
目前已实现 Dashboard 标题、植物选择、四张当前状态卡片、四张历史曲线图和预警展示；AI 建议和聊天仍待实现。

```sh
cd '/Users/jia/P1 Program/ACS Greenhouse/frontend'
npm ci
npm run dev
```

生产构建：`npm run build`；预览：`npm run preview`。

目录与文件已按约定建立。App.jsx 已接入 Dashboard.jsx；SensorCard、HistoryChart、AlertPanel 和植物选择已可用；RecommendationCard 和 ChatBox 仍为占位组件。mockData.js 提供当前与历史传感器及植物预警示例数据。
安装位置和卸载命令见 ../docs/前端依赖安装与卸载记录.md。

## 目录结构

```text
frontend/
├── src/
│   ├── components/
│   │   ├── SensorCard.jsx
│   │   ├── HistoryChart.jsx
│   │   ├── AlertPanel.jsx
│   │   ├── RecommendationCard.jsx
│   │   └── ChatBox.jsx
│   ├── pages/
│   │   └── Dashboard.jsx
│   ├── services/
│   │   └── api.js
│   ├── data/
│   │   └── mockData.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── .env
├── .env.example
├── .gitignore
├── index.html
├── vite.config.js
├── package.json
├── package-lock.json
└── README.md
```

`node_modules/` 是安装的依赖，`dist/` 是构建输出，两者不用于手动编写业务代码。

## 植物选择预留

`PlantSelector.jsx` 可搜索并选择本地示例植物。`Dashboard.jsx` 保存所选 `{ id, name }`；后续预警、建议和聊天请求使用 `id` 作为植物上下文。`services/api.js` 已实现后端文档明确的健康检查与传感器接口，并保留三个植物分析函数签名；由于后端尚无植物分析接口，调用时会明确报错。当前页面不调用这些函数。

现有传感器结构没有 `plantId`，因此当前状态卡片和历史曲线仍代表传感器测到的环境数据；选择植物只会改变未来的植物相关分析上下文。若要按植物分别展示不同传感器数据，需要后端提供植物与传感器或温室区域的关联。

## 已实现的后端 API 封装

`src/services/api.js` 使用 `VITE_API_BASE_URL` 指定后端服务地址（默认 `http://localhost:8000`），自动附加 `/api` 路径。导出传感器函数 `getHealthCheck`、`getSensorReadings`、`createSensorReading`、`getSensorReading`、`getSensorHistory`、`deleteSensorReading`、`deleteSensorHistory`，以及通用 LLM 函数 `generateRecommendation`、`sendGreenhouseMessage`。历史范围仅接受 `1h`、`24h`、`7d`、`30d`。响应即使是 HTTP 200，只要正文包含 `error`，也会作为错误处理。

Dashboard 当前使用 mockData.js 展示四张状态卡片，并调用 `getSensorHistory` 获取四张历史图的数据。后端历史接口不可用时显示带来源标识的示例曲线；如果接口成功返回空数组则显示空状态。POST 与 DELETE 仅为文档接口封装，没有加入普通 Dashboard 操作。

## 当前状态卡片

四张卡片复用 `src/components/SensorCard.jsx`，从 `mockData.currentReadings` 读取 `temperature`、`humidity`、`soil_moisture`、`light`。`mockData.sensorStatuses` 仅用于演示 `Normal` / `Low` 标签，尚不代表后端按所选植物计算的真实状态。选择植物不会改变传感器读数；等后端提供植物关联和状态判定后，再接入真实数据。

## 通用 LLM 接口

`generateRecommendation({ hours: 24, language: 'en' })` 调用 `POST /api/llm/recommend/`，返回建议文本和所用传感器上下文。`sendGreenhouseMessage(message, 'en')` 调用 `POST /api/llm/chat/`，返回回答文本与 `context_used`。这两个接口没有 `plantId`，因此暂不接入需要按所选植物分析的 UI。后端当前 `zh` 语言映射有误，调用时保持 `en`。

## 历史曲线

`HistoryChart.jsx` 使用 Recharts 复用四次，分别读取 `temperature`、`humidity`、`soil_moisture` 和 `light`。Dashboard 的 `1 Week` / `1 Month` 按钮分别请求 `/api/sensors/history/7d/` 和 `/api/sensors/history/30d/`。后端文档约定数据按时间从旧到新返回；横轴使用 UTC 日期标签，提示框显示指标值。后端不可用时显示 `mockData.history` 中的对应时间段示例数据，并标明来源。

## 预警展示

`AlertPanel.jsx` 展示当前所选植物的预警。未选植物时提示先选择；选中 Tomato 显示一条低土壤湿度示例预警，Basil 和 Lettuce 显示暂无预警。示例预警从 `mockData.alerts` 按 `plantId` 筛选，前端不根据传感器读数自行判定。后端提供植物预警接口后，再将示例数据替换为接口响应。
