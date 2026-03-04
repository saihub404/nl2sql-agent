import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import QueryConsole from "./pages/QueryConsole";
import Transparency from "./pages/Transparency";
import Analytics from "./pages/Analytics";
import History from "./pages/History";
import DataUpload from "./pages/DataUpload";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<QueryConsole />} />
          <Route path="/transparency" element={<Transparency />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/history" element={<History />} />
          <Route path="/upload" element={<DataUpload />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
