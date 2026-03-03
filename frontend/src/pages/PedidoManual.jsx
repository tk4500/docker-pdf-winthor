import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import ClientSearch from '../components/ClientSearch';
import ProductSearch from '../components/ProductSearch';
import { Save, ArrowLeft, Plus, Trash2, ShoppingCart } from 'lucide-react';

export default function PedidoManual() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [pedido, setPedido] = useState({
    numero_pedido: "",
    cliente: null,
    itens: [],
    options: { auto_process: true, is_bonificacao: false }
  });

  const handleClientSelect = (cliWinthor) => {
    setPedido(prev => ({ ...prev, cliente: cliWinthor }));
  };

  const addNewItem = () => {
    if (!pedido.cliente) return alert("Selecione um cliente primeiro.");
    const newItem = { id: Date.now(), produto: null, quantidade: 1, valor_unitario: 0, valor_total: 0 };
    setPedido(prev => ({ ...prev, itens: [...prev.itens, newItem] }));
  };

  const updateItemValue = (index, field, value) => {
    const novosItens = [...pedido.itens];
    novosItens[index][field] = value;
    const qtd = parseFloat(novosItens[index].quantidade) || 0;
    const val = parseFloat(novosItens[index].valor_unitario) || 0;
    novosItens[index].valor_total = (qtd * val).toFixed(2);
    setPedido(prev => ({ ...prev, itens: novosItens }));
  };

  const handleProductSelect = async (index, prodWinthor) => {
    const novosItens = [...pedido.itens];
    novosItens[index].produto = prodWinthor;
    setPedido(prev => ({ ...prev, itens: novosItens }));
    try {
      const { data } = await api.post('/produtos/preco', { cliente_id: pedido.cliente.id, produto_id: prodWinthor.id });
      if (data.encontrado) {
        novosItens[index].valor_unitario = parseFloat(data.preco).toFixed(2);
        novosItens[index].valor_total = (parseFloat(novosItens[index].quantidade) * data.preco).toFixed(2);
        setPedido(prev => ({ ...prev, itens: [...novosItens] }));
      }
    } catch (e) { console.error(e); }
  };

  // --- NAVEGAÇÃO POR TECLADO ---
  const handleNumPedidoKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (pedido.itens.length === 0) addNewItem();
      // O ProductSearch da primeira linha já vai ganhar foco pelo autoFocus
    }
  };

  const handleQtdKeyDown = (e, idx) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const el = document.getElementById(`val-input-${idx}`);
      el?.focus(); el?.select();
    }
  };

  const handleValKeyDown = (e, idx) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addNewItem();
    }
  };

  const handleSave = async () => {
    const validItens = pedido.itens.filter(i => i.produto);
    if (!pedido.cliente || validItens.length === 0) return alert("Dados incompletos.");
    setSaving(true);
    try {
      const { data } = await api.post('/pedidos/manual', {
        numero_pedido: pedido.numero_pedido,
        cliente_id: pedido.cliente.id,
        options: pedido.options,
        itens: validItens.map(i => ({ id_produto: i.produto.id, quantidade: i.quantidade, valor: i.valor_unitario }))
      });
      navigate(`/pedido/${data.job_id}`);
    } catch (e) { alert("Erro ao salvar."); } finally { setSaving(false); }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <button onClick={() => navigate('/')} className="flex items-center text-gray-600 font-medium hover:text-blue-600"><ArrowLeft className="mr-1 w-5 h-5" /> Voltar</button>
        <h1 className="text-2xl font-bold flex items-center"><ShoppingCart className="mr-2 text-blue-600" /> Digitação</h1>
        <button onClick={handleSave} disabled={saving || !pedido.cliente} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md font-bold disabled:bg-green-300">
          {saving ? 'Gravando...' : 'Gerar Pedido'}
        </button>
      </div>

      <div className="bg-white p-6 rounded-lg shadow mb-6 border-t-4 border-blue-600">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-1">
            <label className="block text-sm font-medium mb-1">Nº Pedido</label>
            <input id="num-pedido-input" type="text" className="w-full border rounded p-2 outline-none focus:ring-2 focus:ring-blue-500" 
              value={pedido.numero_pedido} onChange={e => setPedido({...pedido, numero_pedido: e.target.value})} onKeyDown={handleNumPedidoKeyDown} />
          </div>
          <div className="md:col-span-3">
            <label className="block text-sm font-medium mb-1">Cliente</label>
            <ClientSearch onSelect={handleClientSelect} />
          </div>
        </div>
      </div>

      <div className={`bg-white shadow rounded-lg overflow-visible ${!pedido.cliente ? 'opacity-50 pointer-events-none' : ''}`}>
        <div className="p-4 bg-gray-50 border-b flex justify-between rounded-t-lg">
          <h3 className="font-bold">Itens do Pedido</h3>
          <span className="font-bold text-green-700">Total: R$ {pedido.itens.reduce((acc, i) => acc + parseFloat(i.valor_total), 0).toFixed(2)}</span>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100 text-xs text-gray-500 uppercase">
            <tr><th className="px-4 py-3 text-left w-1/2">Produto</th><th className="px-4 py-3 text-right">Qtd</th><th className="px-4 py-3 text-right">Preço</th><th className="px-4 py-3 text-right">Total</th><th className="px-4 py-3"></th></tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {pedido.itens.map((item, idx) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  {!item.produto ? <ProductSearch autoFocus={true} rowIndex={idx} onSelect={p => handleProductSelect(idx, p)} /> : <div className="text-sm font-medium">{item.produto.id} - {item.produto.nome}</div>}
                </td>
                <td className="px-4 py-3 text-right">
                  <input id={`qtd-input-${idx}`} type="number" className="w-20 border rounded p-1 text-right outline-none focus:ring-2 focus:ring-blue-500" 
                    value={item.quantidade} onChange={e => updateItemValue(idx, 'quantidade', e.target.value)} onKeyDown={e => handleQtdKeyDown(e, idx)} />
                </td>
                <td className="px-4 py-3 text-right">
                  <input id={`val-input-${idx}`} type="number" step="0.01" className="w-24 border rounded p-1 text-right outline-none focus:ring-2 focus:ring-blue-500" 
                    value={item.valor_unitario} onChange={e => updateItemValue(idx, 'valor_unitario', e.target.value)} onKeyDown={e => handleValKeyDown(e, idx)} />
                </td>
                <td className="px-4 py-3 text-right font-bold">R$ {item.valor_total}</td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => setPedido(prev => ({...prev, itens: prev.itens.filter((_, i) => i !== idx)}))} className="text-red-400 hover:text-red-600"><Trash2 className="w-5 h-5" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="p-4 bg-gray-50 rounded-b-lg border-t">
          <button onClick={addNewItem} className="text-blue-600 font-bold flex items-center text-sm"><Plus className="mr-1 w-4 h-4" /> Adicionar Produto</button>
        </div>
      </div>
    </div>
  );
}