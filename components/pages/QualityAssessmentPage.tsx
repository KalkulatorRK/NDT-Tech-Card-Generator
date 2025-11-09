import React, { useState } from 'react';
import Card from '../shared/Card';
import Input from '../shared/Input';
import Button from '../shared/Button';
import Spinner from '../shared/Spinner';
import { assessQuality } from '../../services/geminiService';

interface Defect {
    id: string;
    type: string;
    size: string;
}

const generateUniqueId = () => `defect_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

const QualityAssessmentPage: React.FC = () => {
    const [method, setMethod] = useState('Радиографический');
    const [normativeDoc, setNormativeDoc] = useState('ГОСТ 7512');
    const [thickness, setThickness] = useState('3.6');
    const [defects, setDefects] = useState<Defect[]>([{ id: generateUniqueId(), type: 'Одиночное включение', size: '1.2' }]);

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [assessmentResult, setAssessmentResult] = useState<string | null>(null);

    const handleAddDefect = () => {
        setDefects([...defects, { id: generateUniqueId(), type: '', size: '' }]);
    };

    const handleRemoveDefect = (id: string) => {
        setDefects(defects.filter(d => d.id !== id));
    };

    const handleDefectChange = (id: string, field: 'type' | 'size', value: string) => {
        setDefects(defects.map(d => d.id === id ? { ...d, [field]: value } : d));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);
        setAssessmentResult(null);

        try {
            const defectData = defects.map(({ type, size }) => ({ type, size })).filter(d => d.type && d.size);
            if (defectData.length === 0) {
                setError("Пожалуйста, добавьте хотя бы один дефект с типом и размером.");
                setIsLoading(false);
                return;
            }
            const result = await assessQuality(method, normativeDoc, thickness, defectData);
            setAssessmentResult(result);
        } catch (err: any) {
            setError(err.message || 'Произошла ошибка при оценке');
        } finally {
            setIsLoading(false);
        }
    };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-2">Оценка качества сварного соединения</h1>
      <p className="text-slate-600 mb-8">Введите параметры дефектов для получения заключения о качестве в соответствии с нормативным документом.</p>

      <form onSubmit={handleSubmit}>
        <Card>
            <h2 className="text-xl font-bold text-slate-800 border-b-2 border-primary-200 pb-2 mb-6">Исходные данные</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="ndt-method" className="block text-sm font-medium text-gray-700 mb-1">Метод контроля</label>
                <select id="ndt-method" value={method} onChange={(e) => setMethod(e.target.value)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md">
                  <option>Радиографический</option>
                  <option>Визуальный и измерительный</option>
                  <option>Капиллярный</option>
                </select>
              </div>
               <div>
                <label htmlFor="normative-doc" className="block text-sm font-medium text-gray-700 mb-1">Нормативный документ</label>
                <select id="normative-doc" value={normativeDoc} onChange={(e) => setNormativeDoc(e.target.value)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md">
                  <option>ГОСТ 7512</option>
                  <option>НП-105-18</option>
                  <option>ГОСТ Р 50.05.7-19</option>
                </select>
              </div>
               <Input label="Толщина стенки, мм" type="number" placeholder="3.6" value={thickness} onChange={(e) => setThickness(e.target.value)} />
            </div>
        </Card>

        <Card className="mt-6">
            <h2 className="text-xl font-bold text-slate-800 border-b-2 border-primary-200 pb-2 mb-6">Обнаруженные дефекты</h2>
            <div className="space-y-4">
                {defects.map((defect) => (
                     <div key={defect.id} className="flex items-end gap-4 p-3 bg-slate-50 rounded-lg">
                         <div className="flex-1">
                            <label htmlFor={`defect-type-${defect.id}`} className="block text-sm font-medium text-gray-700 mb-1">Тип дефекта</label>
                            <select id={`defect-type-${defect.id}`} value={defect.type} onChange={(e) => handleDefectChange(defect.id, 'type', e.target.value)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md">
                              <option value="">-- Выберите тип --</option>
                              <option>Одиночное включение</option>
                              <option>Скопление</option>
                              <option>Трещина</option>
                              <option>Непровар</option>
                            </select>
                        </div>
                        <Input label="Размер, мм" type="number" value={defect.size} onChange={(e) => handleDefectChange(defect.id, 'size', e.target.value)} className="flex-1" />
                        <Button type="button" variant="danger" size="sm" onClick={() => handleRemoveDefect(defect.id)}>Удалить</Button>
                    </div>
                ))}
            </div>
            <div className="mt-4">
                <Button type="button" variant="secondary" onClick={handleAddDefect}>Добавить дефект</Button>
            </div>
        </Card>
        
        <div className="mt-8 flex justify-end">
            <Button type="submit" size="lg" disabled={isLoading}>
                {isLoading ? <><Spinner className="mr-2" /> Оцениваем...</> : 'Провести оценку'}
            </Button>
        </div>
      </form>
      
      {error && <p className="mt-4 text-center text-red-600">{error}</p>}

      {assessmentResult && (
          <Card className="mt-8">
              <h2 className="text-xl font-bold text-slate-800 mb-4">Результат оценки</h2>
              <div className="p-4 bg-slate-50 rounded-md whitespace-pre-wrap">{assessmentResult}</div>
          </Card>
      )}

    </div>
  );
};

export default QualityAssessmentPage;
