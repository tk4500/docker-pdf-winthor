import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';       // <--- Importe
import PedidoEdit from './pages/PedidoEdit'; // <--- Importe
import PedidoManual from './pages/PedidoManual'; // <--- Importe
import Historico from './pages/Historico'; // <--- Importe

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" />;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* Dashboard */}
        <Route path="/" element={
          <PrivateRoute><Dashboard /></PrivateRoute>
        } />

        {/* Upload Novo */}
        <Route path="/upload" element={
          <PrivateRoute><Upload /></PrivateRoute>
        } />

        {/* Edição do Pedido (Recebe o ID do job) */}
        <Route path="/pedido/:id" element={
          <PrivateRoute><PedidoEdit /></PrivateRoute>
        } />

        {/* Digitação Manual */}
        <Route path="/digitar" element={
          <PrivateRoute><PedidoManual /></PrivateRoute>
        } />
        
        <Route path="/historico" element={
          <PrivateRoute><Historico /></PrivateRoute>
        } />

      </Routes>
    </BrowserRouter>
  );
}