import { create } from 'zustand';

interface ProjectDashboardState {
  isCreateOverlayOpen: boolean;
  openCreateOverlay: () => void;
  closeCreateOverlay: () => void;
}

export const useProjectDashboardStore = create<ProjectDashboardState>((set) => ({
  isCreateOverlayOpen: false,
  openCreateOverlay: () => set({ isCreateOverlayOpen: true }),
  closeCreateOverlay: () => set({ isCreateOverlayOpen: false }),
}));
