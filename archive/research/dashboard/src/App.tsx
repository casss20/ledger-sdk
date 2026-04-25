import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { StatsGrid } from '@/components/stats-grid';
import { ApprovalQueue } from '@/components/approval-queue';
import { KillSwitches } from '@/components/kill-switches';
import { AuditLog } from '@/components/audit-log';
import { GovernanceGraph } from '@/components/governance-graph';
import { RecursiveGroupGraph } from '@/components/recursive-group-graph';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Shield, Activity, GitGraph, Table2, RefreshCw, FolderTree } from 'lucide-react';
import { fetchStats } from '@/lib/api';

function App() {
  const [view, setView] = useState<'table' | 'flow' | 'groups'>('flow');
  
  const { data: stats, refetch } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    refetchInterval: 2000,
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Citadel Governance
              </h1>
              <p className="text-sm text-slate-500">
                AI Action Approval & Audit System
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="border-slate-700 text-slate-400"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Badge
              variant="outline"
              className="border-green-500/30 text-green-400 bg-green-500/10"
            >
              <Activity className="w-3 h-3 mr-1" />
              Live
            </Badge>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="max-w-7xl mx-auto mb-6">
        <StatsGrid />
      </div>

      {/* View Toggle */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center gap-2 bg-slate-900/50 p-1 rounded-lg w-fit border border-slate-800">
          <Button
            variant={view === 'table' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setView('table')}
            className={view === 'table' ? 'bg-slate-700' : 'text-slate-400'}
          >
            <Table2 className="w-4 h-4 mr-2" />
            Table
          </Button>
          <Button
            variant={view === 'flow' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setView('flow')}
            className={view === 'flow' ? 'bg-slate-700' : 'text-slate-400'}
          >
            <GitGraph className="w-4 h-4 mr-2" />
            Flow
          </Button>
          <Button
            variant={view === 'groups' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setView('groups')}
            className={view === 'groups' ? 'bg-slate-700' : 'text-slate-400'}
          >
            <FolderTree className="w-4 h-4 mr-2" />
            Groups
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto">
        {view === 'flow' && (
          <div className="space-y-6">
            {/* Flow Graph View */}
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                  <GitGraph className="w-5 h-5 text-blue-400" />
                  Governance Flow
                  <span className="text-xs font-normal text-slate-500 ml-2">
                    Agent → Risk → Approval → Action → Audit
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <GovernanceGraph />
              </CardContent>
            </Card>

            {/* Bottom section: Approval Queue + Kill Switches side by side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ApprovalQueue />
              <KillSwitches />
            </div>
          </div>
        )}
        
        {view === 'groups' && (
          <div className="space-y-6">
            {/* Recursive Groups View */}
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                  <FolderTree className="w-5 h-5 text-green-400" />
                  Action Groups
                  <span className="text-xs font-normal text-slate-500 ml-2">
                    Weft-style recursive composability — 100 actions look like 5 blocks
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <RecursiveGroupGraph />
              </CardContent>
            </Card>

            {/* Stats for groups */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-400">
                    Total Actions
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-100">8</div>
                  <p className="text-xs text-slate-500 mt-1">Across 7 groups</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-400">
                    Nested Depth
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-100">3</div>
                  <p className="text-xs text-slate-500 mt-1">Root → Group → Subgroup → Action</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-400">
                    Collapsible Groups
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-100">100%</div>
                  <p className="text-xs text-slate-500 mt-1">All groups support fold/unfold</p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
          /* Table View */
          <Tabs defaultValue="approvals" className="w-full">
            <TabsList className="bg-slate-900/50 border border-slate-800 mb-6">
              <TabsTrigger
                value="approvals"
                className="data-[state=active]:bg-slate-800"
              >
                Approval Queue
              </TabsTrigger>
              <TabsTrigger
                value="killswitches"
                className="data-[state=active]:bg-slate-800"
              >
                Kill Switches
              </TabsTrigger>
              <TabsTrigger
                value="audit"
                className="data-[state=active]:bg-slate-800"
              >
                Audit Log
              </TabsTrigger>
            </TabsList>

            <TabsContent value="approvals" className="mt-0">
              <ApprovalQueue />
            </TabsContent>

            <TabsContent value="killswitches" className="mt-0">
              <KillSwitches />
            </TabsContent>

            <TabsContent value="audit" className="mt-0">
              <AuditLog />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}

export default App;
