import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import ProductSearch from '../components/ProductSearch';
import ClientSearch from '../components/ClientSearch';
import { Save, ArrowLeft, AlertCircle, CheckCircle, Edit3, Plus, Trash2 } from 'lucide-react';

export default function PedidoEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [pedido, setPedido] = useState(null);

  // Controle de opções de envio
  const [options, setOptions] = useState({
    is_bonificacao: false,
    force_ai: false
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadJob();
  }, [id]);

  const loadJob = async () => {
    try {
      const { data } = await api.get(`/pedidos/status/${id}`);
      setJob(data);

      // Carrega as opções do banco
      setOptions({
        is_bonificacao: data.resultado?.is_bonificacao || false,
        force_ai: data.resultado?.force_ai || false
      });

      if (data.resultado && data.resultado.pedidos && data.resultado.pedidos.length > 0) {
        setPedido(data.resultado.pedidos[0]);
      }
    } catch (error) {
      console.error(error);
      alert("Erro ao carregar pedido. Veja o console.");
    } finally {
      setLoading(false);
    }
  };

  const updatePedidoHeader = (field, value) => {
    setPedido({ ...pedido, [field]: value });
  };

  const updateClient = (cliWinthor) => {
    setPedido({
      ...pedido,
      dados_cliente: {
        ...pedido.dados_cliente,
        id_winthor: cliWinthor.id,
        razao_social: cliWinthor.razao_social,
        cnpj_original: cliWinthor.cnpj_cpf
      }
    });
  };

  const updateItem = (index, field, value) => {
    const novosItens = [...pedido.itens];
    novosItens[index][field] = value;

    if (field === 'quantidade_total' || field === 'valor_unitario') {
      const qtd = parseFloat(novosItens[index].quantidade_total) || 0;
      const val = parseFloat(novosItens[index].valor_unitario) || 0;
      novosItens[index].valor_total_calculado = (qtd * val).toFixed(2);
    }
    setPedido({ ...pedido, itens: novosItens });
  };

  // Remove um item do array
  const removeItem = (index) => {
    if (!window.confirm("Remover este item do pedido?")) return;

    const novosItens = [...pedido.itens];
    novosItens.splice(index, 1); // Remove 1 elemento na posição index
    setPedido({ ...pedido, itens: novosItens });
  };

  // Adiciona uma linha em branco no final
  const addNewItem = () => {
    const newItem = {
      descricao: "Item Adicionado Manualmente",
      codigo_referencia: "",
      ean: "",
      id_produto_winthor: null,
      descricao_winthor: "",
      quantidade_total: 1,
      valor_unitario: 0.00,
      valor_total_calculado: 0.00,
      status_item: "CORRIGIDO_MANUAL",
      mensagens: ["Adicionado pelo usuário"]
    };

    setPedido({ ...pedido, itens: [...pedido.itens, newItem] });
  };

  const handleProductSelect = (index, prodWinthor) => {
    const novosItens = [...pedido.itens];
    novosItens[index].id_produto_winthor = prodWinthor.id;
    novosItens[index].descricao_winthor = prodWinthor.nome;
    novosItens[index].status_item = "CORRIGIDO_MANUAL";
    setPedido({ ...pedido, itens: novosItens });
  };

  const handleSaveAndSend = async () => {
    setSaving(true);
    try {
      await api.post(`/pedidos/finalizar/${id}`, {
        pedido: pedido,
        options: options
      });
      alert("Pedido enviado com sucesso para o Winthor!");
      navigate('/');
    } catch (error) {
      alert("Erro ao finalizar: " + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-10 text-center text-gray-600">Carregando dados do pedido...</div>;
  if (!pedido) return <div className="p-10 text-center text-red-500 font-bold">Erro: Pedido sem dados JSON válidos.</div>;

  const totalPdf = parseFloat(pedido.totais?.pdf || 0);
  const totalCalculado = pedido.itens.reduce((acc, item) => acc + (parseFloat(item.valor_total_calculado) || 0), 0);
  const diferenca = totalPdf - totalCalculado;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Cabeçalho */}
      <div className="flex justify-between items-center mb-6">
        <button onClick={() => navigate('/')} className="flex items-center text-gray-600 hover:text-blue-600 font-medium">
          <ArrowLeft className="w-5 h-5 mr-1" /> Voltar
        </button>
        <div className="flex items-center space-x-4">
          <button
            onClick={handleSaveAndSend}
            disabled={saving}
            className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md shadow flex items-center font-bold transition-colors disabled:bg-green-300"
          >
            {saving ? 'Enviando...' : <><Save className="w-5 h-5 mr-2" /> Finalizar Pedido</>}
          </button>
        </div>
      </div>

      {/* Caixa de Edição do Cabeçalho do Pedido */}
      <div className="bg-white p-6 rounded-lg shadow mb-6 border-t-4 border-blue-600">
        <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
          <Edit3 className="w-5 h-5 mr-2 text-blue-600" /> Dados Principais do Pedido
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

          {/* Número do Pedido */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Número do Pedido (PDF)</label>
            <input
              type="text"
              value={pedido.numero_pedido || ''}
              onChange={(e) => updatePedidoHeader('numero_pedido', e.target.value)}
              className="w-full border border-gray-300 rounded p-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Busca de Cliente */}
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cliente
              {!pedido.dados_cliente?.id_winthor && <span className="text-red-500 ml-2 font-bold">(Não Vinculado!)</span>}
            </label>
            <ClientSearch
              initialValue={pedido.dados_cliente?.id_winthor ? `${pedido.dados_cliente.id_winthor} - ${pedido.dados_cliente.razao_social}` : pedido.dados_cliente?.razao_social || ''}
              onSelect={updateClient}
            />
          </div>

          {/* Opções de Envio (Bonificação) */}
          <div className="flex flex-col justify-end pb-2">
            <label className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
              <input
                type="checkbox"
                checked={options.is_bonificacao}
                onChange={(e) => setOptions({ ...options, is_bonificacao: e.target.checked })}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">Bonificação (SaleType 5)</span>
            </label>
          </div>
        </div>

        {/* Totais Visuais */}
        <div className="mt-6 pt-4 border-t border-gray-200 flex flex-wrap gap-8 text-sm">
          <div>
            <span className="text-gray-500 block">Total Lido do PDF</span>
            <span className="font-bold text-lg">R$ {totalPdf.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-500 block">Soma dos Itens Atual</span>
            <span className={`font-bold text-lg ${Math.abs(diferenca) > 0.5 ? 'text-red-600' : 'text-green-600'}`}>
              R$ {totalCalculado.toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-500 block">Status Validação (Backend)</span>
            <span className="font-bold text-gray-800 bg-gray-100 px-2 py-1 rounded">{pedido.status_pedido}</span>
          </div>
        </div>
      </div>

      {/* Tabela de Itens */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto Original (PDF)</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/3">Vínculo Winthor (Busca)</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qtd</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Vlr Unit.</th>
              <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200 text-sm">
            {pedido.itens.map((item, idx) => {
              const hasError = item.status_item !== 'OK' && item.status_item !== 'CORRIGIDO_AUTO' && item.status_item !== 'CORRIGIDO_MANUAL';

              return (
                <tr key={idx} className={hasError ? 'bg-red-50' : 'hover:bg-gray-50'}>
                  {/* Descrição Original do PDF */}
                  <td className="px-3 py-3">
                    <div className="text-gray-900 font-medium">{item.descricao}</div>
                    <div className="text-xs text-gray-500 mt-1">Ref: {item.codigo_referencia || 'N/A'} | EAN: {item.ean || 'N/A'}</div>
                  </td>

                  {/* Busca Winthor */}
                  <td className="px-3 py-3">
                    <ProductSearch
                      initialValue={item.id_produto_winthor ? `${item.id_produto_winthor} - ${item.descricao_winthor || ''}` : ''}
                      onSelect={(prod) => handleProductSelect(idx, prod)}
                    />
                    {!item.id_produto_winthor && <div className="text-xs font-bold text-red-500 mt-1">⚠ Necessário vincular produto</div>}
                  </td>

                  {/* Inputs Editáveis */}
                  <td className="px-3 py-3 text-right">
                    <input
                      type="number"
                      className="w-20 border border-gray-300 rounded p-1 text-right focus:ring-blue-500 focus:border-blue-500"
                      value={item.quantidade_total}
                      onChange={(e) => updateItem(idx, 'quantidade_total', e.target.value)}
                    />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <input
                      type="number"
                      className="w-24 border border-gray-300 rounded p-1 text-right focus:ring-blue-500 focus:border-blue-500"
                      step="0.01"
                      value={item.valor_unitario}
                      onChange={(e) => updateItem(idx, 'valor_unitario', e.target.value)}
                    />
                  </td>
                  <td className="px-3 py-3 text-right font-bold text-gray-700">
                    {parseFloat(item.valor_total_calculado || 0).toFixed(2)}
                  </td>

                  {/* Status */}
                  <td className="px-3 py-3 text-center">
                    {hasError ? (
                      <div className="group relative flex justify-center">
                        <AlertCircle className="text-red-500 w-5 h-5 cursor-help" />
                        <span className="absolute bottom-full mb-2 hidden group-hover:block w-64 bg-gray-900 text-white text-xs rounded p-2 z-50 shadow-lg left-1/2 -translate-x-1/2">
                          {item.mensagens?.join(' | ') || item.status_item}
                        </span>
                      </div>
                    ) : (
                      <CheckCircle className="text-green-500 w-5 h-5 mx-auto" />
                    )}
                  </td>
                  {/* Ações: Botão Remover (NOVA) */}
                  <td className="px-3 py-3 text-center">
                    <button
                      onClick={() => removeItem(idx)}
                      className="text-red-400 hover:text-red-600 transition-colors"
                      title="Remover Item"
                    >
                      <Trash2 className="w-5 h-5 mx-auto" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {/* Botão de Adicionar Item Manual */}
        <div className="bg-gray-50 border-t border-gray-200 p-4">
          <button
            onClick={addNewItem}
            className="flex items-center text-sm text-blue-600 font-bold hover:text-blue-800 transition-colors"
          >
            <Plus className="w-4 h-4 mr-1" /> Adicionar Produto Manualmente
          </button>
        </div>
      </div>
    </div>
  );
}