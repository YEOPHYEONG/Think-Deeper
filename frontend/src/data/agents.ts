export interface Agent {
    name: string;
    role: "critic" | "moderator" | "searcher";
    description: string;
    image: string;
  }
  
  export const agents: Agent[] = [
    {
      name: "Critic",
      role: "critic",
      description: "구조화된 반론과 근거를 제시하는 비판자 에이전트",
      image: "/critic.png",
    },
    {
      name: "Moderator",
      role: "moderator",
      description: "논점 정리와 요약을 도와주는 중재자 에이전트",
      image: "/moderator.png",
    },
    {
      name: "Searcher",
      role: "searcher",
      description: "실시간 정보 검색을 지원하는 검색 에이전트",
      image: "/searcher.png",
    },
  ];
  
  export const roleNameMap: Record<Agent['role'], string> = {
    critic: "비판자",
    moderator: "중재자",
    searcher: "검색자",
  };
  
  export const roles = Object.keys(roleNameMap) as Agent['role'][];
  
  export function getAgentsByRole(role: Agent['role']): Agent[] {
    return agents.filter(agent => agent.role === role);
  }