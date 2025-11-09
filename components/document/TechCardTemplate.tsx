// Fix: Provide full content for the file.
import React, { forwardRef } from 'react';
import { TechCardData } from '../../types';

interface TechCardTemplateProps {
  data: TechCardData;
}

// Using forwardRef to allow the parent component to get a ref to the DOM element
const TechCardTemplate = forwardRef<HTMLDivElement, TechCardTemplateProps>(({ data }, ref) => {
  return (
    // The class names here correspond to the styles in templateStyles.css
    <div ref={ref} className="tech-card-container">
      <header className="tech-card-header">
        <h1>Технологическая карта</h1>
        <h2>на {data.controlMethod.toLowerCase()} контроль</h2>
        <p>№ {data.weldConnectionNumber}</p>
      </header>

      <section>
        <table className="tech-card-table">
          <tbody>
            <tr>
              <th>Заказчик</th>
              <td>{data.customer}</td>
            </tr>
            <tr>
              <th>Объект</th>
              <td>{data.facility}</td>
            </tr>
            <tr>
              <th>Объект контроля</th>
              <td>{data.controlObject}</td>
            </tr>
            <tr>
              <th>Тип сварного соединения</th>
              <td>{data.weldType}</td>
            </tr>
            <tr>
              <th>Толщина, мм / Диаметр, мм</th>
              <td>{data.thickness} / {data.diameter}</td>
            </tr>
            <tr>
              <th>Нормативный документ</th>
              <td>{data.normativeDocument}</td>
            </tr>
            <tr>
                <th>Уровень качества</th>
                <td>{data.qualityLevel}</td>
            </tr>
             <tr>
                <th>Чувствительность</th>
                <td>{data.sensitivity}</td>
            </tr>
            <tr>
                <th>Используемое оборудование</th>
                <td>{data.equipment.join(', ')}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="tech-card-section">
        <h2>1. Порядок проведения контроля</h2>
        <div className="whitespace-pre-wrap">{data.controlProcedure}</div>
      </section>

      <section className="tech-card-section">
        <h2>2. Нормы оценки качества</h2>
        <div className="whitespace-pre-wrap">{data.acceptanceCriteria}</div>
      </section>
      
      <section className="tech-card-section">
        <h2>3. Требования к персоналу</h2>
        <div className="whitespace-pre-wrap">{data.personnelRequirements}</div>
      </section>

      <section className="tech-card-section">
        <h2>4. Требования по технике безопасности</h2>
        <div className="whitespace-pre-wrap">{data.safetyPrecautions}</div>
      </section>
    </div>
  );
});

TechCardTemplate.displayName = 'TechCardTemplate';

export default TechCardTemplate;
