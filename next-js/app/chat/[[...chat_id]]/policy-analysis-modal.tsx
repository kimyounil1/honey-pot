"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { UploadCloud, FileText } from 'lucide-react'
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea" // Textarea 임포트

interface PolicyAnalysisModalProps {
  isOpen: boolean
  onClose: () => void
  onAnalyze: (files: File[], textInput?: string) => void // textInput 추가
}

export default function PolicyAnalysisModal({ isOpen, onClose, onAnalyze }: PolicyAnalysisModalProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [textInput, setTextInput] = useState("") // 텍스트 입력 상태 추가

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFiles(Array.from(event.target.files))
    }
  }

  const handleAnalyze = () => {
    if (selectedFiles.length > 0 || textInput.trim()) {
      onAnalyze(selectedFiles, textInput)
      onClose()
      setSelectedFiles([])
      setTextInput("")
    }
  }

  const handleClose = () => {
    onClose()
    setSelectedFiles([])
    setTextInput("")
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-xl">내 보험 약관 분석</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center flex flex-col items-center justify-center bg-gray-50">
            <UploadCloud className="h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-600 mb-2">여기에 보험약관 pdf 파일을 올려주세요</p>
            <Label htmlFor="file-upload" className="cursor-pointer">
              <Button asChild variant="outline">
                <span>파일 첨부하기</span>
              </Button>
              <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} accept=".pdf,image/*" multiple />
            </Label>
            {selectedFiles.length > 0 && (
              <div className="mt-4 text-sm text-gray-700">
                <p>{selectedFiles.length}개 파일 선택됨:</p>
                <ul className="list-disc list-inside">
                  {selectedFiles.map((file, index) => (
                    <li key={index}>{file.name}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">또는</span>
            </div>
          </div>

          {/* 새로운 채팅 입력창 */}
          <div className="space-y-2">
            <Label htmlFor="policy-text-input">파일이 없으시면, 보험사와 보험명을 입력해주세요</Label>
            <Textarea // Textarea로 변경
              id="policy-text-input"
              placeholder="예: 삼성생명 리빙케어 보험"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              rows={6} // 높이 조절
            />
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button
              onClick={handleAnalyze}
              disabled={selectedFiles.length === 0 && !textInput.trim()}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
            >
              <FileText className="mr-2 h-4 w-4" />분석 시작하기
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
