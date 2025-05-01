import React from 'react';

interface CriticOutputProps {
  critiquePoint: string;
  briefElaboration: string;
  requestSearchQuery?: string | null;
}

const CriticOutput: React.FC<CriticOutputProps> = ({
  critiquePoint,
  briefElaboration,
  requestSearchQuery,
}) => {
  return (
    <div className="p-3 mt-2 bg-white border rounded-xl shadow-sm text-sm space-y-2">
      <div>
        <p className="font-semibold text-gray-800">🧐 핵심 지적</p>
        <p className="text-gray-700">{critiquePoint}</p>
      </div>
      <div>
        <p className="font-semibold text-gray-800">🔍 상세 설명</p>
        <p className="text-gray-700 whitespace-pre-line">{briefElaboration}</p>
      </div>
      {requestSearchQuery && (
        <div>
          <p className="font-semibold text-gray-800">🔎 추천 검색어</p>
          <p className="text-blue-600">{requestSearchQuery}</p>
        </div>
      )}
    </div>
  );
};

export default CriticOutput;
